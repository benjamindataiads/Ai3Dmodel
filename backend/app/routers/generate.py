import json
import re
import base64
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Part, Project
from app.models.part import PartStatus
from app.schemas import PartResponse, PartGenerateRequest, ProjectResponse, ContextPart
from app.services.llm_service import llm_service, OPENAI_MODELS, ANTHROPIC_MODELS, DEFAULT_OPENAI_MODEL, DEFAULT_ANTHROPIC_MODEL
from app.services.cad_service import cad_service
from app.services.parameter_service import parameter_service
from app.services.agent_service import agent_service
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


# Agent-based generation schemas
class AgentMessage(BaseModel):
    role: str
    content: str
    data: dict = {}


class AgentGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None
    existing_code: str | None = None
    context_parts: list[ContextPart] | None = None
    use_optimization: bool = True
    use_review: bool = False
    printer_settings: dict | None = None


class AgentGenerateResponse(BaseModel):
    success: bool
    code: str | None
    bounding_box: dict | None
    validation: dict | None
    suggestions: list[str]
    iterations: int
    messages: list[AgentMessage]
    error: str | None


@router.post("/parts/{part_id}/generate-with-agents", response_model=PartResponse)
async def generate_part_with_agents(
    part_id: UUID,
    request: AgentGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate CadQuery code using multi-agent system for better quality."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    provider = request.provider or settings.default_llm_provider
    
    try:
        context_parts = None
        if request.context_parts:
            context_parts = [(p.name, p.code) for p in request.context_parts]
        
        # Run agent pipeline
        agent_result = await agent_service.generate_with_agents(
            prompt=request.prompt,
            provider=provider,
            model=request.model,
            existing_code=request.existing_code,
            context_parts=context_parts,
            printer_settings=request.printer_settings,
            use_optimization=request.use_optimization,
            use_review=request.use_review,
        )
        
        if agent_result["success"] and agent_result["code"]:
            part.code = agent_result["code"]
            part.prompt = request.prompt
            part.bounding_box = agent_result["bounding_box"]
            part.status = PartStatus.GENERATED
            part.error_message = None
            
            # Extract parameters
            params = parameter_service.extract_parameters(agent_result["code"])
            part.parameters = params
        else:
            part.status = PartStatus.ERROR
            part.error_message = agent_result.get("error") or "Agent generation failed"
            
    except Exception as e:
        part.status = PartStatus.ERROR
        part.error_message = str(e)
    
    await db.commit()
    await db.refresh(part)
    return part


@router.post("/parts/{part_id}/generate-with-image", response_model=PartResponse)
async def generate_part_with_image(
    part_id: UUID,
    prompt: str = Form(...),
    image: UploadFile = File(...),
    provider: str = Form(None),
    model: str = Form(None),
    use_optimization: bool = Form(True),
    db: AsyncSession = Depends(get_db),
):
    """Generate CadQuery code from an image and description using vision AI."""
    query = select(Part).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )
    
    # Validate image type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(allowed_types)}",
        )
    
    # Read and encode image
    image_content = await image.read()
    image_data = base64.b64encode(image_content).decode("utf-8")
    image_mime_type = image.content_type
    
    provider_to_use = provider or settings.default_llm_provider
    
    try:
        # Run agent pipeline with image
        agent_result = await agent_service.generate_with_agents(
            prompt=prompt,
            provider=provider_to_use,
            model=model,
            image_data=image_data,
            image_mime_type=image_mime_type,
            use_optimization=use_optimization,
            use_review=True,  # Enable review when image is provided
        )
        
        if agent_result["success"] and agent_result["code"]:
            part.code = agent_result["code"]
            part.prompt = f"[Image] {prompt}"
            part.bounding_box = agent_result["bounding_box"]
            part.status = PartStatus.GENERATED
            part.error_message = None
            
            params = parameter_service.extract_parameters(agent_result["code"])
            part.parameters = params
        else:
            part.status = PartStatus.ERROR
            part.error_message = agent_result.get("error") or "Image-based generation failed"
            
    except Exception as e:
        part.status = PartStatus.ERROR
        part.error_message = str(e)
    
    await db.commit()
    await db.refresh(part)
    return part


@router.post("/analyze-image")
async def analyze_image_for_design(
    image: UploadFile = File(...),
    prompt: str = Form(""),
    provider: str = Form(None),
    model: str = Form(None),
):
    """Analyze an image and return design suggestions without generating code."""
    from app.prompts.agent_prompts import DESIGN_WITH_IMAGE_PROMPT
    
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(allowed_types)}",
        )
    
    image_content = await image.read()
    image_data = base64.b64encode(image_content).decode("utf-8")
    
    provider_to_use = provider or settings.default_llm_provider
    
    analysis_prompt = f"""Analyse cette image pour la conception 3D.

{f"Contexte additionnel: {prompt}" if prompt else ""}

Décris:
1. La forme générale de l'objet
2. Les dimensions estimées (en mm)
3. Les features visibles (trous, rainures, etc.)
4. La complexité pour l'impression 3D
5. Les primitives CadQuery à utiliser

Réponds en JSON:
{{
  "shape_description": "...",
  "estimated_dimensions": {{"length": X, "width": Y, "height": Z}},
  "features": ["..."],
  "complexity": "simple|medium|complex",
  "suggested_primitives": ["box", "cylinder", etc.],
  "printability_notes": "...",
  "recommended_approach": "..."
}}"""
    
    try:
        response = await agent_service._generate_with_vision(
            analysis_prompt,
            "Tu es un expert en analyse d'images pour la conception 3D. Tu identifies les formes, dimensions et caractéristiques des objets pour leur reproduction en CAO.",
            image_data,
            image.content_type,
            provider_to_use,
            model,
        )
        
        # Try to parse as JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            analysis = json.loads(json_match.group())
            return {"success": True, "analysis": analysis}
        else:
            return {"success": True, "analysis": {"raw_response": response}}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {str(e)}",
        )


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


# Image-based project generation
class ImageData(BaseModel):
    data: str  # Base64 encoded image data
    mime_type: str
    name: str


class ProjectGenerateWithImagesRequest(BaseModel):
    prompt: str = ""
    images: list[ImageData] = []
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None


@router.post("/projects/generate-with-images", response_model=ProjectGenerateResponse)
async def generate_project_with_images(
    request: ProjectGenerateWithImagesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete project with multiple parts from images and description."""
    from app.prompts.project_system import PROJECT_SYSTEM_PROMPT
    from sqlalchemy.orm import selectinload
    
    provider = request.provider or settings.default_llm_provider
    
    if not request.prompt and not request.images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a description or images"
        )
    
    try:
        # Build prompt with image context
        prompt_parts = []
        if request.prompt:
            prompt_parts.append(f"Description du projet: {request.prompt}")
        
        if request.images:
            prompt_parts.append(f"\n{len(request.images)} image(s) de référence fournie(s):")
            for i, img in enumerate(request.images):
                prompt_parts.append(f"  - Image {i+1}: {img.name}")
            prompt_parts.append("\nAnalyse ces images pour comprendre la forme, les proportions et les fonctionnalités souhaitées.")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Prepare images for vision
        image_data = []
        for img in request.images:
            image_data.append((img.data, img.mime_type))
        
        # Generate project structure via LLM with vision
        if image_data:
            response = await llm_service.generate_with_vision(
                full_prompt,
                PROJECT_SYSTEM_PROMPT,
                image_data,
                provider,
                model=request.model
            )
        else:
            response = await llm_service.generate_raw(
                full_prompt,
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
            start_idx = response.find('{')
            if start_idx != -1:
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
        
        data = json.loads(json_str)
        project_name = data.get("project_name", "Nouveau projet")
        parts_data = data.get("parts", [])
        
        if not parts_data:
            raise ValueError("No parts generated")
        
        # Create project
        project = Project(name=project_name)
        db.add(project)
        await db.flush()
        
        # Create and process each part
        generated_parts = []
        for part_data in parts_data:
            part_name = part_data.get("name", "Part")
            part_code = part_data.get("code", "")
            part_desc = part_data.get("description", "")
            
            part = Part(
                project_id=project.id,
                name=part_name,
                code=part_code,
                prompt=part_desc,
            )
            
            try:
                params = parameter_service.extract_parameters(part_code)
                part.parameters = params
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
