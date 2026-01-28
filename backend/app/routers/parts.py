from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, Part, PartVersion
from app.models.part import PartStatus
from app.schemas import (
    PartCreate,
    PartUpdate,
    PartResponse,
    PartParametersUpdate,
    PartValidateRequest,
    PartValidateResponse,
    BoundingBox,
)
from app.services.cad_service import cad_service
from app.services.parameter_service import parameter_service


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
    return version

router = APIRouter()

# Router for project-scoped operations (mounted at /api)
project_parts_router = APIRouter()


@project_parts_router.post(
    "/projects/{project_id}/parts",
    response_model=PartResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["parts"],
)
async def create_part(
    project_id: UUID,
    part_in: PartCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new part in a project."""
    # Check project exists
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    part = Part(project_id=project_id, **part_in.model_dump())
    
    # If code is provided, try to extract parameters and execute
    if part.code:
        try:
            params = parameter_service.extract_parameters(part.code)
            part.parameters = params
            
            result = await cad_service.execute_code(part.code)
            if result.success:
                part.bounding_box = result.bounding_box
                part.status = PartStatus.GENERATED
            else:
                part.status = PartStatus.ERROR
                part.error_message = result.error
        except Exception as e:
            part.status = PartStatus.ERROR
            part.error_message = str(e)
    
    db.add(part)
    await db.commit()
    await db.refresh(part)
    return part


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a part by ID."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    return part


@router.put("/{part_id}", response_model=PartResponse)
async def update_part(
    part_id: UUID,
    part_in: PartUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a part and re-execute if code changed."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    update_data = part_in.model_dump(exclude_unset=True)
    code_changed = "code" in update_data and update_data["code"] != part.code
    
    for field, value in update_data.items():
        setattr(part, field, value)
    
    # Re-execute if code changed
    if code_changed and part.code:
        try:
            params = parameter_service.extract_parameters(part.code)
            part.parameters = params
            
            result = await cad_service.execute_code(part.code)
            if result.success:
                part.bounding_box = result.bounding_box
                part.status = PartStatus.GENERATED
                part.error_message = None
            else:
                part.status = PartStatus.ERROR
                part.error_message = result.error
        except Exception as e:
            part.status = PartStatus.ERROR
            part.error_message = str(e)
    
    await db.commit()
    await db.refresh(part)
    return part


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_part(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a part."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    await db.delete(part)
    await db.commit()


class ExecuteRequest(BaseModel):
    code: str


class AutosaveRequest(BaseModel):
    code: str


@router.post("/{part_id}/autosave", response_model=PartResponse)
async def autosave_part_code(
    part_id: UUID,
    request: AutosaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Autosave code without executing. Creates a version snapshot."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    # Only save if code actually changed
    if part.code != request.code:
        # Create version of current state before updating
        if part.code:
            await create_version(db, part, source="autosave")
        
        # Update code without executing
        part.code = request.code
        
        # Extract parameters (quick operation, no CAD execution)
        try:
            params = parameter_service.extract_parameters(request.code)
            part.parameters = params
        except Exception:
            pass  # Ignore parameter extraction errors in autosave
        
        await db.commit()
        await db.refresh(part)
    
    return part


@router.post("/{part_id}/execute", response_model=PartResponse)
async def execute_part_code(
    part_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute code and update part (always runs, even if code unchanged)."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    # Create version of current state before updating
    if part.code:
        await create_version(db, part, source="manual")
    
    # Update code
    part.code = request.code
    
    # Extract parameters and execute
    try:
        params = parameter_service.extract_parameters(request.code)
        part.parameters = params
        
        result = await cad_service.execute_code(request.code)
        if result.success:
            part.bounding_box = result.bounding_box
            part.status = PartStatus.GENERATED
            part.error_message = None
        else:
            part.status = PartStatus.ERROR
            part.error_message = result.error
    except Exception as e:
        part.status = PartStatus.ERROR
        part.error_message = str(e)
    
    await db.commit()
    await db.refresh(part)
    return part


@router.get("/{part_id}/parameters")
async def get_part_parameters(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get extracted parameters and bounding box for a part."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    return {
        "parameters": part.parameters or [],
        "bounding_box": part.bounding_box,
    }


@router.put("/{part_id}/parameters", response_model=PartResponse)
async def update_part_parameters(
    part_id: UUID,
    params_in: PartParametersUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update parameters and regenerate part."""
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
            detail="Part has no code to update",
        )
    
    # Validate parameters
    is_valid, error_msg = parameter_service.validate_parameters(params_in.parameters)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    
    # Inject new parameter values into code
    try:
        new_code = parameter_service.inject_parameters(part.code, params_in.parameters)
        part.code = new_code
        
        # Re-extract parameters and execute
        params = parameter_service.extract_parameters(new_code)
        part.parameters = params
        
        result = await cad_service.execute_code(new_code)
        if result.success:
            part.bounding_box = result.bounding_box
            part.status = PartStatus.GENERATED
            part.error_message = None
        else:
            part.status = PartStatus.ERROR
            part.error_message = result.error
    except Exception as e:
        part.status = PartStatus.ERROR
        part.error_message = str(e)
    
    await db.commit()
    await db.refresh(part)
    return part


@router.post("/{part_id}/validate", response_model=PartValidateResponse)
async def validate_part(
    part_id: UUID,
    validate_in: PartValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate if part fits within build volume."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    if not part.bounding_box:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part has no bounding box (not yet generated)",
        )
    
    bbox = part.bounding_box
    build = validate_in.build_volume
    
    overflow_x = max(0, bbox["x"] - build.x)
    overflow_y = max(0, bbox["y"] - build.y)
    overflow_z = max(0, bbox["z"] - build.z)
    
    fits = overflow_x == 0 and overflow_y == 0 and overflow_z == 0
    
    suggestions = []
    if overflow_x > 0:
        suggestions.append(f"La pièce dépasse de {overflow_x:.1f}mm en X")
    if overflow_y > 0:
        suggestions.append(f"La pièce dépasse de {overflow_y:.1f}mm en Y")
    if overflow_z > 0:
        suggestions.append(f"La pièce dépasse de {overflow_z:.1f}mm en Z")
    
    if not fits:
        suggestions.append("Réduisez les dimensions ou orientez différemment la pièce")
    
    return PartValidateResponse(
        fits_build_volume=fits,
        part_dimensions=BoundingBox(x=bbox["x"], y=bbox["y"], z=bbox["z"]),
        build_volume=build,
        overflow=BoundingBox(x=overflow_x, y=overflow_y, z=overflow_z),
        suggestions=suggestions,
    )
