"""
API routes for conversational design sessions.
"""
import base64
from typing import Literal
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.services.conversation_service import conversation_service, ConversationPhase
from app.config import settings

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Request/Response schemas
class CreateConversationRequest(BaseModel):
    part_id: str | None = None
    initial_prompt: str | None = None
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None


class ConversationMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None


class ConversationResponse(BaseModel):
    session_id: str
    phase: str
    messages: list[dict]
    requirements: dict
    has_code: bool
    code: str | None = None
    needs_response: bool = True
    complete: bool = False


def _build_response(result: dict) -> ConversationResponse:
    """Build standardized response from conversation result."""
    session = result["session"]
    return ConversationResponse(
        session_id=session["id"],
        phase=session["phase"],
        messages=session["messages"],
        requirements=session["requirements"],
        has_code=session["generated_code"] is not None,
        code=session["generated_code"],
        needs_response=result.get("needs_response", True),
        complete=result.get("complete", False),
    )


@router.post("/create", response_model=ConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """Create a new design conversation session."""
    provider = request.provider or settings.default_llm_provider
    
    try:
        session = conversation_service.create_session(
            part_id=request.part_id,
            initial_prompt=request.initial_prompt,
        )
        
        # Start the conversation with agent greeting
        result = await conversation_service.start_conversation(
            session.id,
            provider,
            request.model,
        )
        
        return _build_response(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}",
        )


@router.post("/create-with-image", response_model=ConversationResponse)
async def create_conversation_with_image(
    part_id: str = Form(None),
    initial_prompt: str = Form(None),
    image: UploadFile = File(...),
    provider: str = Form(None),
    model: str = Form(None),
):
    """Create a conversation with a single image reference."""
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(allowed_types)}",
        )
    
    image_content = await image.read()
    image_data = base64.b64encode(image_content).decode("utf-8")
    
    provider_to_use = provider or settings.default_llm_provider
    
    try:
        session = conversation_service.create_session(
            part_id=part_id,
            initial_prompt=initial_prompt,
            image_data=image_data,
            image_mime_type=image.content_type,
        )
        
        result = await conversation_service.start_conversation(
            session.id,
            provider_to_use,
            model,
        )
        
        return _build_response(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}",
        )


class AttachmentData(BaseModel):
    data: str  # Base64 encoded
    mime_type: str = "image/png"
    name: str = ""
    is_sketch: bool = False


class CreateWithAttachmentsRequest(BaseModel):
    part_id: str | None = None
    initial_prompt: str | None = None
    attachments: list[AttachmentData] = []
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None


@router.post("/create-with-attachments", response_model=ConversationResponse)
async def create_conversation_with_attachments(request: CreateWithAttachmentsRequest):
    """Create a conversation with multiple images/sketches."""
    if len(request.attachments) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 attachments allowed",
        )
    
    provider_to_use = request.provider or settings.default_llm_provider
    
    # Convert to dict format for service
    attachments = [
        {
            "data": att.data,
            "mime_type": att.mime_type,
            "name": att.name,
            "is_sketch": att.is_sketch,
        }
        for att in request.attachments
    ]
    
    try:
        session = conversation_service.create_session(
            part_id=request.part_id,
            initial_prompt=request.initial_prompt,
            attachments=attachments,
        )
        
        result = await conversation_service.start_conversation(
            session.id,
            provider_to_use,
            request.model,
        )
        
        return _build_response(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}",
        )


@router.post("/{session_id}/add-attachment")
async def add_attachment_to_session(
    session_id: str,
    image: UploadFile = File(...),
    name: str = Form(""),
    is_sketch: bool = Form(False),
):
    """Add an attachment to an existing conversation."""
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    if len(session.attachments) >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 attachments reached",
        )
    
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(allowed_types)}",
        )
    
    image_content = await image.read()
    image_data = base64.b64encode(image_content).decode("utf-8")
    
    attachment = conversation_service.add_attachment(
        session_id,
        data=image_data,
        mime_type=image.content_type,
        name=name or image.filename or "",
        is_sketch=is_sketch,
    )
    
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add attachment",
        )
    
    return {
        "status": "added",
        "attachment_id": attachment.id,
        "total_attachments": len(session.attachments),
    }


@router.get("/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str):
    """Get conversation state."""
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    return ConversationResponse(
        session_id=session.id,
        phase=session.phase.value,
        messages=[m.to_dict() for m in session.messages],
        requirements=session.requirements.to_dict(),
        has_code=session.generated_code is not None,
        code=session.generated_code,
        needs_response=session.phase != ConversationPhase.COMPLETE,
        complete=session.phase == ConversationPhase.COMPLETE,
    )


@router.post("/{session_id}/message", response_model=ConversationResponse)
async def send_message(session_id: str, request: ConversationMessageRequest):
    """Send a message in the conversation."""
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    provider = request.provider or settings.default_llm_provider
    
    try:
        result = await conversation_service.process_user_message(
            session_id,
            request.message,
            provider,
            request.model,
        )
        
        return _build_response(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post("/{session_id}/quick-action")
async def quick_action(
    session_id: str,
    action: str,
    provider: str = None,
    model: str = None,
):
    """Execute a quick action in the conversation."""
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    provider_to_use = provider or settings.default_llm_provider
    
    # Map actions to messages
    action_messages = {
        "proceed": "Oui, continue",
        "finalize": "Finaliser",
        "modify": "J'ai des modifications",
        "restart": "Recommencer",
        "skip": "Passer cette question",
    }
    
    message = action_messages.get(action, action)
    
    try:
        result = await conversation_service.process_user_message(
            session_id,
            message,
            provider_to_use,
            model,
        )
        
        return _build_response(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process action: {str(e)}",
        )


@router.delete("/{session_id}")
async def delete_conversation(session_id: str):
    """Delete a conversation session."""
    if conversation_service.delete_session(session_id):
        return {"status": "deleted"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation not found",
    )


@router.post("/{session_id}/apply-to-part")
async def apply_to_part(session_id: str, part_id: str):
    """Apply generated code to a part."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Part
    from app.models.part import PartStatus
    from app.services.cad_service import cad_service
    from app.services.parameter_service import parameter_service
    
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    if not session.generated_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No generated code in conversation",
        )
    
    async with async_session() as db:
        query = select(Part).where(Part.id == part_id)
        result = await db.execute(query)
        part = result.scalar_one_or_none()
        
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Part not found",
            )
        
        try:
            part.code = session.generated_code
            part.prompt = session.requirements.description
            
            # Extract parameters
            params = parameter_service.extract_parameters(session.generated_code)
            part.parameters = params
            
            # Execute to validate
            exec_result = await cad_service.execute_code(session.generated_code)
            
            if exec_result.success:
                part.bounding_box = exec_result.bounding_box
                part.status = PartStatus.GENERATED
                part.error_message = None
            else:
                part.status = PartStatus.ERROR
                part.error_message = exec_result.error
            
            await db.commit()
            await db.refresh(part)
            
            return {
                "status": "applied",
                "part_id": str(part.id),
                "part_status": part.status.value,
            }
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to apply code: {str(e)}",
            )
