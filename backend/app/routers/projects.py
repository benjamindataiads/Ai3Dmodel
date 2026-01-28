from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Project, Part
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)

router = APIRouter()


@router.get("", response_model=list[ProjectListResponse])
async def list_projects(
    section_id: UUID | None = None,
    unsectioned: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List projects with parts count. Filter by section or get unsectioned projects."""
    query = (
        select(
            Project,
            func.count(Part.id).label("parts_count"),
        )
        .outerjoin(Part)
        .group_by(Project.id)
    )
    
    if unsectioned:
        query = query.where(Project.section_id.is_(None))
    elif section_id:
        query = query.where(Project.section_id == section_id)
    
    query = query.order_by(Project.position, Project.updated_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        ProjectListResponse(
            id=row.Project.id,
            name=row.Project.name,
            description=row.Project.description,
            section_id=row.Project.section_id,
            position=row.Project.position,
            created_at=row.Project.created_at,
            updated_at=row.Project.updated_at,
            parts_count=row.parts_count,
        )
        for row in rows
    ]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = Project(**project_in.model_dump())
    db.add(project)
    await db.commit()
    
    # Re-fetch with parts relationship loaded
    query = (
        select(Project)
        .options(selectinload(Project.parts))
        .where(Project.id == project.id)
    )
    result = await db.execute(query)
    return result.scalar_one()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a project by ID with all its parts."""
    query = (
        select(Project)
        .options(selectinload(Project.parts))
        .where(Project.id == project_id)
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    query = (
        select(Project)
        .options(selectinload(Project.parts))
        .where(Project.id == project_id)
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project and all its parts."""
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a project with all its parts."""
    # Get original project with parts
    query = (
        select(Project)
        .options(selectinload(Project.parts))
        .where(Project.id == project_id)
    )
    result = await db.execute(query)
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Create new project
    new_project = Project(
        name=f"{original.name} (copie)",
        description=original.description,
        section_id=original.section_id,
        position=original.position + 1,
    )
    db.add(new_project)
    await db.flush()
    
    # Duplicate parts
    for part in original.parts:
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
    
    # Reload with parts
    query = (
        select(Project)
        .options(selectinload(Project.parts))
        .where(Project.id == new_project.id)
    )
    result = await db.execute(query)
    return result.scalar_one()


@router.patch("/{project_id}/move", response_model=ProjectResponse)
async def move_project(
    project_id: UUID,
    section_id: UUID | None = None,
    position: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Move a project to a different section or position."""
    query = (
        select(Project)
        .options(selectinload(Project.parts))
        .where(Project.id == project_id)
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Update section if provided (can be None to unsection)
    project.section_id = section_id
    
    if position is not None:
        project.position = position
    
    await db.commit()
    await db.refresh(project)
    return project
