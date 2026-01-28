"""Router for importing 3D files."""
import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, Part
from app.models.part import PartStatus
from app.schemas import PartResponse
from app.services.import_service import import_service
from app.config import settings


router = APIRouter(prefix="/import", tags=["import"])

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/file", response_model=PartResponse)
async def import_file(
    project_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import a 3D file (STL, OBJ, 3MF) and create a new part."""
    # Verify project exists
    project_query = select(Project).where(Project.id == project_id)
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check file extension
    filename = file.filename or "unknown"
    allowed_extensions = ['.stl', '.obj', '.3mf']
    ext = os.path.splitext(filename.lower())[1]
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}",
        )
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )
    
    # Reset file position for parsing
    import io
    file_obj = io.BytesIO(content)
    
    # Parse the file
    import_result = import_service.import_file(file_obj, filename)
    
    if not import_result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=import_result.error or "Failed to parse file",
        )
    
    # Generate a name from filename
    part_name = os.path.splitext(filename)[0]
    
    # Store mesh data as JSON for the viewer
    mesh_data = {
        "vertices": import_result.vertices,
        "faces": import_result.faces,
        "source_file": filename,
    }
    
    # Calculate dimensions from bounding box for the schema
    bb = import_result.bounding_box
    bounding_box_data = {
        "x": bb["max_x"] - bb["min_x"],
        "y": bb["max_y"] - bb["min_y"],
        "z": bb["max_z"] - bb["min_z"],
    }
    
    # Create the part with imported mesh
    part = Part(
        project_id=project_id,
        name=part_name,
        code=f"# Imported from: {filename}\n# This part was imported from a 3D file.\n# Vertices: {len(import_result.vertices)}\n# Faces: {len(import_result.faces)}",
        status=PartStatus.GENERATED,
        bounding_box=bounding_box_data,
        parameters=[
            {"name": "vertices_count", "value": float(len(import_result.vertices)), "line": 3, "unit": ""},
            {"name": "faces_count", "value": float(len(import_result.faces)), "line": 4, "unit": ""},
        ],
    )
    
    # Store mesh data in a separate field - we need to add this to the model
    # For now, we'll save it as a temp file
    import json
    mesh_path = os.path.join(settings.temp_dir, f"{part.id}_mesh.json")
    with open(mesh_path, 'w') as f:
        json.dump(mesh_data, f)
    
    db.add(part)
    await db.commit()
    await db.refresh(part)
    
    return part


@router.get("/mesh/{part_id}")
async def get_imported_mesh(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the mesh data for an imported part."""
    import json
    
    # Verify part exists
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    # Try to load mesh data
    mesh_path = os.path.join(settings.temp_dir, f"{part_id}_mesh.json")
    
    if not os.path.exists(mesh_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesh data not found",
        )
    
    with open(mesh_path, 'r') as f:
        mesh_data = json.load(f)
    
    return mesh_data
