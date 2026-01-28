import json
import re
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Part, Project
from app.models.part import PartStatus
from app.schemas import PartResponse, PartGenerateRequest, ProjectResponse
from app.services.llm_service import llm_service, OPENAI_MODELS, ANTHROPIC_MODELS, DEFAULT_OPENAI_MODEL, DEFAULT_ANTHROPIC_MODEL
from app.services.cad_service import cad_service
from app.services.parameter_service import parameter_service
from app.config import settings

router = APIRouter()


@router.get("/models")
async def get_available_models():
    """Get available models for each provider."""
    return {
        "openai": {
            "models": [{"id": k, "name": v} for k, v in OPENAI_MODELS.items()],
            "default": DEFAULT_OPENAI_MODEL,
        },
        "anthropic": {
            "models": [{"id": k, "name": v} for k, v in ANTHROPIC_MODELS.items()],
            "default": DEFAULT_ANTHROPIC_MODEL,
        },
    }


# Assembly AI schemas
class PartPositionInfo(BaseModel):
    id: str
    name: str
    bounding_box: dict  # {x, y, z}
    current_position: dict  # {x, y, z, rotX, rotY, rotZ}


class AssemblyRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    parts: list[PartPositionInfo]
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None


class PartPosition(BaseModel):
    x: float = 0
    y: float = 0
    z: float = 0
    rotX: float = 0
    rotY: float = 0
    rotZ: float = 0


class AssemblyResponse(BaseModel):
    positions: dict[str, PartPosition]


# Project generation schemas
class ProjectGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None


class GeneratedPartInfo(BaseModel):
    name: str
    description: str
    status: str
    error: str | None = None


class ProjectGenerateResponse(BaseModel):
    project_id: str
    project_name: str
    parts: list[GeneratedPartInfo]


@router.post("/parts/{part_id}/generate", response_model=PartResponse)
async def generate_part_code(
    part_id: UUID,
    request: PartGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate CadQuery code from natural language description."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    # Determine provider
    provider = request.provider or settings.default_llm_provider
    
    try:
        # Prepare context parts if provided
        context_parts = None
        if request.context_parts:
            context_parts = [(p.name, p.code) for p in request.context_parts]
        
        # Generate code via LLM
        code = await llm_service.generate_cad_code(
            request.prompt, 
            provider,
            existing_code=request.existing_code,
            context_parts=context_parts,
            model=request.model
        )
        
        part.code = code
        part.prompt = request.prompt
        
        # Extract parameters
        params = parameter_service.extract_parameters(code)
        part.parameters = params
        
        # Execute code to validate and get bounding box
        result = await cad_service.execute_code(code)
        
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


@router.post("/assembly/position", response_model=AssemblyResponse)
async def generate_assembly_positions(
    request: AssemblyRequest,
):
    """Generate part positions from natural language instruction."""
    from app.prompts.assembly_system import ASSEMBLY_SYSTEM_PROMPT
    
    # Build the context about current parts
    parts_info = []
    for p in request.parts:
        parts_info.append(
            f"- {p.name} (id: {p.id})\n"
            f"  Dimensions: {p.bounding_box['x']:.1f} x {p.bounding_box['y']:.1f} x {p.bounding_box['z']:.1f} mm\n"
            f"  Position actuelle: X={p.current_position['x']:.1f}, Y={p.current_position['y']:.1f}, Z={p.current_position['z']:.1f}\n"
            f"  Rotation actuelle: rotX={p.current_position['rotX']:.1f}°, rotY={p.current_position['rotY']:.1f}°, rotZ={p.current_position['rotZ']:.1f}°"
        )
    
    parts_context = "\n".join(parts_info)
    
    user_prompt = f"""PIÈCES DISPONIBLES:
{parts_context}

INSTRUCTION: {request.prompt}

Retourne les nouvelles positions au format JSON."""
    
    provider = request.provider or settings.default_llm_provider
    
    try:
        response = await llm_service.generate_raw(
            user_prompt,
            ASSEMBLY_SYSTEM_PROMPT,
            provider,
            model=request.model
        )
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("No JSON found in response")
        
        json_str = json_match.group()
        data = json.loads(json_str)
        
        # Validate and build response
        positions = {}
        for part_id, pos in data.get("positions", {}).items():
            positions[part_id] = PartPosition(
                x=float(pos.get("x", 0)),
                y=float(pos.get("y", 0)),
                z=float(pos.get("z", 0)),
                rotX=float(pos.get("rotX", 0)),
                rotY=float(pos.get("rotY", 0)),
                rotZ=float(pos.get("rotZ", 0)),
            )
        
        return AssemblyResponse(positions=positions)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON in LLM response: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate positions: {str(e)}"
        )


@router.post("/projects/generate", response_model=ProjectGenerateResponse)
async def generate_project(
    request: ProjectGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete project with multiple parts from a description."""
    from app.prompts.project_system import PROJECT_SYSTEM_PROMPT
    from sqlalchemy.orm import selectinload
    
    provider = request.provider or settings.default_llm_provider
    
    try:
        # Generate project structure via LLM
        response = await llm_service.generate_raw(
            f"Projet à créer: {request.prompt}",
            PROJECT_SYSTEM_PROMPT,
            provider,
            model=request.model
        )
        
        # Extract JSON from response - try multiple methods
        json_str = None
        
        # Method 1: Try to extract from ```json ... ``` block
        json_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if json_block_match:
            json_str = json_block_match.group(1)
        
        # Method 2: Find the outermost JSON object
        if not json_str:
            # Find first { and last } to get the complete JSON object
            start_idx = response.find('{')
            if start_idx != -1:
                # Count braces to find matching closing brace
                depth = 0
                end_idx = start_idx
                in_string = False
                escape_next = False
                for i, char in enumerate(response[start_idx:], start_idx):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                    if not in_string:
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0:
                                end_idx = i
                                break
                json_str = response[start_idx:end_idx + 1]
        
        if not json_str:
            raise ValueError("No JSON found in LLM response")
        
        # Try to parse, with cleanup on failure
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try to fix common issues: unescaped newlines in code strings
            # Replace literal newlines in strings with \n
            fixed_json = json_str
            # This is a simplified fix - in production you'd want more robust handling
            raise ValueError(f"Invalid JSON in LLM response: {str(e)}")
        
        project_name = data.get("project_name", "Nouveau projet")
        parts_data = data.get("parts", [])
        
        if not parts_data:
            raise ValueError("No parts generated")
        
        # Create project
        project = Project(name=project_name)
        db.add(project)
        await db.flush()  # Get the project ID
        
        # Create and process each part
        generated_parts = []
        for part_data in parts_data:
            part_name = part_data.get("name", "Part")
            part_code = part_data.get("code", "")
            part_desc = part_data.get("description", "")
            
            # Create part
            part = Part(
                project_id=project.id,
                name=part_name,
                code=part_code,
                prompt=part_desc,
            )
            
            # Try to execute the code
            try:
                # Extract parameters
                params = parameter_service.extract_parameters(part_code)
                part.parameters = params
                
                # Execute code
                result = await cad_service.execute_code(part_code)
                
                if result.success:
                    part.bounding_box = result.bounding_box
                    part.status = PartStatus.GENERATED
                    part.error_message = None
                    generated_parts.append(GeneratedPartInfo(
                        name=part_name,
                        description=part_desc,
                        status="generated"
                    ))
                else:
                    part.status = PartStatus.ERROR
                    part.error_message = result.error
                    generated_parts.append(GeneratedPartInfo(
                        name=part_name,
                        description=part_desc,
                        status="error",
                        error=result.error
                    ))
            except Exception as e:
                part.status = PartStatus.ERROR
                part.error_message = str(e)
                generated_parts.append(GeneratedPartInfo(
                    name=part_name,
                    description=part_desc,
                    status="error",
                    error=str(e)
                ))
            
            db.add(part)
        
        await db.commit()
        
        return ProjectGenerateResponse(
            project_id=str(project.id),
            project_name=project_name,
            parts=generated_parts
        )
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON in LLM response: {str(e)}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate project: {str(e)}"
        )
