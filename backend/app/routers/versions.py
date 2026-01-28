import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Part, PartVersion
from app.schemas.version import VersionResponse, VersionSummary


router = APIRouter(prefix="/versions", tags=["versions"])


async def create_version(
    db: AsyncSession,
    part: Part,
    source: str = "manual",
) -> PartVersion:
    """Create a new version snapshot of a part."""
    version = PartVersion(
        part_id=part.id,
        code=part.code,
        prompt=part.prompt,
        parameters=part.parameters,
        bounding_box=part.bounding_box,
        status=part.status.value if hasattr(part.status, 'value') else str(part.status),
        error_message=part.error_message,
        source=source,
    )
    db.add(version)
    await db.flush()
    return version


@router.get("/part/{part_id}", response_model=list[VersionSummary])
async def list_part_versions(
    part_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all versions for a part, most recent first."""
    # Verify part exists
    part_query = select(Part).where(Part.id == part_id)
    result = await db.execute(part_query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    # Get versions
    query = (
        select(PartVersion)
        .where(PartVersion.part_id == part_id)
        .order_by(desc(PartVersion.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    versions = result.scalars().all()
    
    return [
        {
            "id": v.id,
            "source": v.source,
            "status": v.status,
            "created_at": v.created_at,
            "has_code": bool(v.code),
        }
        for v in versions
    ]


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific version."""
    query = select(PartVersion).where(PartVersion.id == version_id)
    result = await db.execute(query)
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return version


@router.post("/{version_id}/restore", response_model=VersionResponse)
async def restore_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Restore a part to a specific version."""
    # Get the version
    query = select(PartVersion).where(PartVersion.id == version_id)
    result = await db.execute(query)
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Get the part
    part_query = select(Part).where(Part.id == version.part_id)
    result = await db.execute(part_query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    # Create a version of current state before restoring
    await create_version(db, part, source="before_restore")
    
    # Restore the part to the version's state
    part.code = version.code
    part.prompt = version.prompt
    part.parameters = version.parameters
    part.bounding_box = version.bounding_box
    part.status = version.status
    part.error_message = version.error_message
    
    await db.commit()
    
    # Create a version marking the restore
    await create_version(db, part, source="restore")
    await db.commit()
    
    return version
