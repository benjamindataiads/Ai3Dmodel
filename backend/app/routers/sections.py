import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Section, Project, Part
from app.schemas.section import (
    SectionCreate,
    SectionUpdate,
    SectionResponse,
    SectionWithProjects,
)


router = APIRouter(prefix="/sections", tags=["sections"])


@router.get("", response_model=list[SectionWithProjects])
async def list_sections(db: AsyncSession = Depends(get_db)):
    """List all sections with their projects."""
    # Load sections with projects and parts (nested eager loading)
    query = (
        select(Section)
        .options(
            selectinload(Section.projects).selectinload(Project.parts)
        )
        .order_by(Section.position, Section.created_at)
    )
    result = await db.execute(query)
    sections = result.scalars().all()
    
    # Build response with project counts
    response = []
    for section in sections:
        section_dict = {
            "id": section.id,
            "name": section.name,
            "color": section.color,
            "position": section.position,
            "created_at": section.created_at,
            "updated_at": section.updated_at,
            "projects_count": len(section.projects),
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "position": p.position,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "parts_count": len(p.parts),
                }
                for p in sorted(section.projects, key=lambda x: (x.position, x.created_at))
            ],
        }
        response.append(section_dict)
    
    return response


@router.post("", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    section_in: SectionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new section."""
    # Get max position
    result = await db.execute(select(func.max(Section.position)))
    max_pos = result.scalar() or 0
    
    section = Section(
        **section_in.model_dump(),
        position=max_pos + 1,
    )
    db.add(section)
    await db.commit()
    await db.refresh(section)
    
    return {
        **section.__dict__,
        "projects_count": 0,
    }


@router.get("/{section_id}", response_model=SectionWithProjects)
async def get_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a section by ID."""
    query = (
        select(Section)
        .options(
            selectinload(Section.projects).selectinload(Project.parts)
        )
        .where(Section.id == section_id)
    )
    result = await db.execute(query)
    section = result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return {
        "id": section.id,
        "name": section.name,
        "color": section.color,
        "position": section.position,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
        "projects_count": len(section.projects),
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "position": p.position,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "parts_count": len(p.parts),
            }
            for p in sorted(section.projects, key=lambda x: (x.position, x.created_at))
        ],
    }


@router.patch("/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: uuid.UUID,
    section_in: SectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a section."""
    query = select(Section).where(Section.id == section_id)
    result = await db.execute(query)
    section = result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    update_data = section_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(section, key, value)
    
    await db.commit()
    await db.refresh(section)
    
    # Get project count
    count_query = select(func.count(Project.id)).where(Project.section_id == section_id)
    count_result = await db.execute(count_query)
    projects_count = count_result.scalar() or 0
    
    return {
        **section.__dict__,
        "projects_count": projects_count,
    }


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a section. Projects in the section will become unsectioned."""
    query = select(Section).where(Section.id == section_id)
    result = await db.execute(query)
    section = result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Move projects to unsectioned (set section_id to null)
    await db.execute(
        Project.__table__.update()
        .where(Project.section_id == section_id)
        .values(section_id=None)
    )
    
    await db.delete(section)
    await db.commit()


@router.post("/{section_id}/duplicate", response_model=SectionWithProjects)
async def duplicate_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a section with all its projects and parts."""
    # Get original section with projects
    query = (
        select(Section)
        .options(
            selectinload(Section.projects).selectinload(Project.parts)
        )
        .where(Section.id == section_id)
    )
    result = await db.execute(query)
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Get max position
    pos_result = await db.execute(select(func.max(Section.position)))
    max_pos = pos_result.scalar() or 0
    
    # Create new section
    new_section = Section(
        name=f"{original.name} (copie)",
        color=original.color,
        position=max_pos + 1,
    )
    db.add(new_section)
    await db.flush()
    
    # Duplicate projects and their parts
    for project in original.projects:
        new_project = Project(
            name=project.name,
            description=project.description,
            section_id=new_section.id,
            position=project.position,
        )
        db.add(new_project)
        await db.flush()
        
        # Duplicate parts
        for part in project.parts:
            new_part = Part(
                project_id=new_project.id,
                name=part.name,
                code=part.code,
                prompt=part.prompt,
                status=part.status,
                error_message=part.error_message,
            )
            db.add(new_part)
    
    await db.commit()
    
    # Reload with relationships
    query = (
        select(Section)
        .options(selectinload(Section.projects))
        .where(Section.id == new_section.id)
    )
    result = await db.execute(query)
    section = result.scalar_one()
    
    return {
        "id": section.id,
        "name": section.name,
        "color": section.color,
        "position": section.position,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
        "projects_count": len(section.projects),
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "position": p.position,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "parts_count": 0,
            }
            for p in sorted(section.projects, key=lambda x: (x.position, x.created_at))
        ],
    }
