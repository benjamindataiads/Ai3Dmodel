from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Project, Part
from app.services.cad_service import cad_service
from app.services.export_service import export_service

router = APIRouter()


@router.get("/parts/{part_id}/preview")
async def get_part_preview(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get STL file for 3D preview."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    if not part.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part has no code",
        )
    
    try:
        stl_path = await cad_service.generate_stl(part.code, str(part_id))
        return FileResponse(
            stl_path,
            media_type="model/stl",
            filename=f"{part.name}.stl",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}",
        )


@router.get("/parts/{part_id}/export/stl")
async def export_part_stl(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export part as STL file."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    if not part.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part has no code",
        )
    
    try:
        stl_path = await export_service.export_stl(part.code, str(part_id), part.name)
        return FileResponse(
            stl_path,
            media_type="model/stl",
            filename=f"{part.name}.stl",
            headers={"Content-Disposition": f'attachment; filename="{part.name}.stl"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export STL: {str(e)}",
        )


@router.get("/parts/{part_id}/export/3mf")
async def export_part_3mf(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export part as 3MF file (compatible with Bambu Studio)."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    if not part.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part has no code",
        )
    
    try:
        threemf_path = await export_service.export_3mf(part.code, str(part_id), part.name)
        return FileResponse(
            threemf_path,
            media_type="application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
            filename=f"{part.name}.3mf",
            headers={"Content-Disposition": f'attachment; filename="{part.name}.3mf"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export 3MF: {str(e)}",
        )


@router.get("/projects/{project_id}/export/3mf")
async def export_project_3mf(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export entire project as 3MF file with all parts."""
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
    
    parts_with_code = [p for p in project.parts if p.code]
    
    if not parts_with_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no parts with code",
        )
    
    try:
        threemf_path = await export_service.export_project_3mf(
            [(p.code, p.name) for p in parts_with_code],
            str(project_id),
            project.name,
        )
        return FileResponse(
            threemf_path,
            media_type="application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
            filename=f"{project.name}.3mf",
            headers={"Content-Disposition": f'attachment; filename="{project.name}.3mf"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export project: {str(e)}",
        )
