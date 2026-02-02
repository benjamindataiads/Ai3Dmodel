"""
Conversational multi-agent system for interactive 3D model design.

This system enables agents to communicate with users, ask clarifying questions,
and collaboratively refine designs through dialogue.

Model strategy:
- Fast models (Haiku/Nano) for agent conversations (questions, analysis)
- Best models (Opus/GPT-5.2 Pro) for final code generation
"""
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

from app.config import settings


def get_fast_model(provider: str) -> str:
    """Get the fast model for agent conversations (cheap & fast)."""
    if provider == "anthropic":
        return "claude-haiku-4-5-20251001"
    return "gpt-5-nano"


def get_best_model(provider: str) -> str:
    """Get the best model for final code generation (most capable)."""
    if provider == "anthropic":
        return "claude-opus-4-5-20251101"
    return "gpt-5.2-pro"


class AgentRole(str, Enum):
    """Specialized agent roles in the design process."""
    COORDINATOR = "coordinator"      # Orchestrates conversation, decides which agent speaks
    REQUIREMENTS = "requirements"    # Gathers initial requirements, asks clarifying questions
    DESIGNER = "designer"           # Focuses on aesthetics, ergonomics, form
    ENGINEER = "engineer"           # Technical CAD implementation
    PHYSICS = "physics"             # Structural integrity, weight, balance, forces
    MANUFACTURING = "manufacturing"  # 3D printing constraints, materials, tolerances
    VALIDATOR = "validator"         # Code validation, error checking


class MessageType(str, Enum):
    """Types of messages in the conversation."""
    USER = "user"                   # User input
    AGENT = "agent"                 # Agent response
    QUESTION = "question"           # Agent asking user a question
    SUGGESTION = "suggestion"       # Agent making a suggestion
    CODE = "code"                   # Generated code
    VALIDATION = "validation"       # Validation results
    SYSTEM = "system"               # System messages


class ConversationPhase(str, Enum):
    """Phases of the design conversation."""
    GATHERING = "gathering"         # Gathering requirements
    ANALYZING = "analyzing"         # Analyzing requirements
    DESIGNING = "designing"         # Active design phase
    REVIEWING = "reviewing"         # Review and refinement
    FINALIZING = "finalizing"       # Final code generation
    COMPLETE = "complete"           # Conversation complete


@dataclass
class ConversationMessage:
    """A message in the conversation."""
    id: str
    type: MessageType
    agent_role: AgentRole | None
    content: str
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "agent_role": self.agent_role.value if self.agent_role else None,
            "content": self.content,
            "data": self.data,
            "timestamp": self.timestamp,
        }


@dataclass
class DesignRequirements:
    """Structured requirements gathered from conversation."""
    # Basic info
    description: str = ""
    purpose: str = ""
    
    # Dimensions
    dimensions_specified: bool = False
    length: float | None = None
    width: float | None = None
    height: float | None = None
    
    # Physical properties
    needs_structural_analysis: bool = False
    expected_load: float | None = None  # in kg
    material: str = "PLA"
    wall_thickness: float | None = None
    
    # Aesthetics
    style: str = ""  # minimal, organic, industrial, etc.
    finish: str = ""  # smooth, textured, etc.
    has_fillets: bool = True
    fillet_radius: float | None = None
    
    # Functional features
    features: list[str] = field(default_factory=list)  # holes, slots, threads, etc.
    
    # Manufacturing
    printer_type: str = "FDM"
    max_build_volume: dict | None = None
    layer_height: float = 0.2
    needs_supports: bool | None = None
    orientation_preference: str | None = None
    
    # Assembly
    is_part_of_assembly: bool = False
    mating_parts: list[str] = field(default_factory=list)
    tolerances: dict = field(default_factory=dict)
    
    # Confidence scores for each section
    confidence: dict = field(default_factory=lambda: {
        "dimensions": 0.0,
        "purpose": 0.0,
        "features": 0.0,
        "manufacturing": 0.0,
    })
    
    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "purpose": self.purpose,
            "dimensions": {
                "specified": self.dimensions_specified,
                "length": self.length,
                "width": self.width,
                "height": self.height,
            },
            "physical": {
                "needs_structural_analysis": self.needs_structural_analysis,
                "expected_load": self.expected_load,
                "material": self.material,
                "wall_thickness": self.wall_thickness,
            },
            "aesthetics": {
                "style": self.style,
                "finish": self.finish,
                "has_fillets": self.has_fillets,
                "fillet_radius": self.fillet_radius,
            },
            "features": self.features,
            "manufacturing": {
                "printer_type": self.printer_type,
                "max_build_volume": self.max_build_volume,
                "layer_height": self.layer_height,
                "needs_supports": self.needs_supports,
                "orientation_preference": self.orientation_preference,
            },
            "assembly": {
                "is_part_of_assembly": self.is_part_of_assembly,
                "mating_parts": self.mating_parts,
                "tolerances": self.tolerances,
            },
            "confidence": self.confidence,
        }


@dataclass
class ImageAttachment:
    """An image or sketch attachment."""
    id: str
    data: str  # Base64 encoded
    mime_type: str
    name: str = ""
    is_sketch: bool = False


@dataclass
class ConversationSession:
    """A design conversation session."""
    id: str
    part_id: str | None
    phase: ConversationPhase
    messages: list[ConversationMessage]
    requirements: DesignRequirements
    generated_code: str | None = None
    # Support multiple images/sketches
    attachments: list[ImageAttachment] = field(default_factory=list)
    # Legacy single image support
    image_data: str | None = None
    image_mime_type: str | None = None
    context_parts: list[tuple[str, str]] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "phase": self.phase.value,
            "messages": [m.to_dict() for m in self.messages],
            "requirements": self.requirements.to_dict(),
            "generated_code": self.generated_code,
            "has_image": self.image_data is not None or len(self.attachments) > 0,
            "attachments_count": len(self.attachments),
            "attachments": [
                {"id": a.id, "name": a.name, "is_sketch": a.is_sketch}
                for a in self.attachments
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    def has_visual_reference(self) -> bool:
        """Check if session has any visual references (images or sketches)."""
        return self.image_data is not None or len(self.attachments) > 0
    
    def get_all_images(self) -> list[tuple[str, str]]:
        """Get all images as (data, mime_type) tuples."""
        images = []
        
        # Add attachments first
        for att in self.attachments:
            images.append((att.data, att.mime_type))
        
        # Add legacy single image if present and no attachments
        if self.image_data and not self.attachments:
            images.append((self.image_data, self.image_mime_type or "image/jpeg"))
        
        return images
    
    def add_message(
        self,
        type: MessageType,
        content: str,
        agent_role: AgentRole | None = None,
        data: dict | None = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            id=str(uuid.uuid4()),
            type=type,
            agent_role=agent_role,
            content=content,
            data=data or {},
        )
        self.messages.append(msg)
        self.updated_at = datetime.utcnow().isoformat()
        return msg


# In-memory session storage (in production, use Redis or database)
_sessions: dict[str, ConversationSession] = {}


class ConversationService:
    """Service for managing design conversations with multiple agents."""
    
    def __init__(self):
        self.min_confidence_to_proceed = 0.7
    
    def create_session(
        self,
        part_id: str | None = None,
        initial_prompt: str | None = None,
        image_data: str | None = None,
        image_mime_type: str | None = None,
        attachments: list[dict] | None = None,
        context_parts: list[tuple[str, str]] | None = None,
    ) -> ConversationSession:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        
        # Convert attachment dicts to ImageAttachment objects
        attachment_objects = []
        if attachments:
            for i, att in enumerate(attachments):
                attachment_objects.append(ImageAttachment(
                    id=att.get("id", str(uuid.uuid4())),
                    data=att.get("data", ""),
                    mime_type=att.get("mime_type", "image/png"),
                    name=att.get("name", f"Attachment {i+1}"),
                    is_sketch=att.get("is_sketch", False),
                ))
        
        session = ConversationSession(
            id=session_id,
            part_id=part_id,
            phase=ConversationPhase.GATHERING,
            messages=[],
            requirements=DesignRequirements(),
            attachments=attachment_objects,
            image_data=image_data,
            image_mime_type=image_mime_type,
            context_parts=context_parts,
        )
        
        if initial_prompt:
            session.requirements.description = initial_prompt
            session.add_message(
                type=MessageType.USER,
                content=initial_prompt,
            )
        
        # Add note about attachments
        if attachment_objects:
            sketch_count = sum(1 for a in attachment_objects if a.is_sketch)
            image_count = len(attachment_objects) - sketch_count
            parts = []
            if sketch_count:
                parts.append(f"{sketch_count} dessin(s)")
            if image_count:
                parts.append(f"{image_count} image(s)")
            session.add_message(
                type=MessageType.SYSTEM,
                content=f"📎 {' et '.join(parts)} ajouté(s) comme référence",
            )
        
        _sessions[session_id] = session
        return session
    
    def add_attachment(
        self,
        session_id: str,
        data: str,
        mime_type: str,
        name: str = "",
        is_sketch: bool = False,
    ) -> ImageAttachment | None:
        """Add an attachment to an existing session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        attachment = ImageAttachment(
            id=str(uuid.uuid4()),
            data=data,
            mime_type=mime_type,
            name=name or f"Attachment {len(session.attachments) + 1}",
            is_sketch=is_sketch,
        )
        
        session.attachments.append(attachment)
        session.updated_at = datetime.utcnow().isoformat()
        
        return attachment
    
    def get_session(self, session_id: str) -> ConversationSession | None:
        """Get an existing session."""
        return _sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in _sessions:
            del _sessions[session_id]
            return True
        return False
    
    async def process_user_message(
        self,
        session_id: str,
        message: str,
        provider: Literal["openai", "anthropic"],
        model: str | None = None,
    ) -> dict:
        """Process a user message and get agent response."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Add user message
        session.add_message(type=MessageType.USER, content=message)
        
        # Determine which agent should respond based on phase
        if session.phase == ConversationPhase.GATHERING:
            return await self._handle_gathering_phase(session, provider, model)
        elif session.phase == ConversationPhase.ANALYZING:
            return await self._handle_analyzing_phase(session, provider, model)
        elif session.phase == ConversationPhase.DESIGNING:
            return await self._handle_designing_phase(session, provider, model)
        elif session.phase == ConversationPhase.REVIEWING:
            return await self._handle_reviewing_phase(session, provider, model)
        elif session.phase == ConversationPhase.FINALIZING:
            return await self._handle_finalizing_phase(session, provider, model)
        
        return {"session": session.to_dict(), "needs_response": False}
    
    async def start_conversation(
        self,
        session_id: str,
        provider: Literal["openai", "anthropic"],
        model: str | None = None,
    ) -> dict:
        """Start the conversation with initial agent greeting and questions."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Coordinator introduces the process
        coordinator_intro = await self._get_coordinator_intro(session, provider, model)
        session.add_message(
            type=MessageType.AGENT,
            agent_role=AgentRole.COORDINATOR,
            content=coordinator_intro["greeting"],
        )
        
        # Requirements agent asks initial questions
        if coordinator_intro.get("initial_questions"):
            questions = coordinator_intro["initial_questions"]
            session.add_message(
                type=MessageType.QUESTION,
                agent_role=AgentRole.REQUIREMENTS,
                content=questions["content"],
                data={"options": questions.get("options", [])},
            )
        
        return {"session": session.to_dict(), "needs_response": True}
    
    async def _handle_gathering_phase(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Handle the requirements gathering phase."""
        from app.services.llm_service import llm_service
        from app.prompts.conversation_prompts import REQUIREMENTS_AGENT_PROMPT
        
        # Build conversation history
        history = self._build_conversation_history(session)
        
        # Requirements agent analyzes and responds
        prompt = f"""Historique de la conversation:
{history}

Exigences actuelles:
{json.dumps(session.requirements.to_dict(), indent=2, ensure_ascii=False)}

Analyse la dernière réponse de l'utilisateur et:
1. Mets à jour les exigences avec les nouvelles informations
2. Évalue la confiance pour chaque section (0.0 à 1.0)
3. Pose une question de suivi si nécessaire, OU
4. Indique que tu as assez d'informations pour passer à la phase de conception

Réponds en JSON:
{{
  "updated_requirements": {{ ... }},  // Exigences mises à jour
  "confidence_scores": {{ "dimensions": 0.8, "purpose": 0.9, ... }},
  "ready_to_design": true/false,
  "next_question": {{
    "content": "Question à poser",
    "options": ["Option 1", "Option 2"],  // optionnel
    "agent": "requirements/designer/physics/manufacturing"
  }},
  "summary": "Résumé de ce que j'ai compris"
}}"""
        
        try:
            # Use fast model for agent conversations
            fast_model = get_fast_model(provider)
            response = await llm_service.generate_raw(
                prompt,
                REQUIREMENTS_AGENT_PROMPT,
                provider,
                fast_model,
                max_tokens=2000,
            )
            
            # Parse response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                # Update requirements
                self._update_requirements(session.requirements, data.get("updated_requirements", {}))
                
                # Update confidence scores
                if "confidence_scores" in data:
                    session.requirements.confidence.update(data["confidence_scores"])
                
                # Add summary message
                if data.get("summary"):
                    session.add_message(
                        type=MessageType.AGENT,
                        agent_role=AgentRole.REQUIREMENTS,
                        content=data["summary"],
                    )
                
                # Check if ready to proceed
                if data.get("ready_to_design"):
                    session.phase = ConversationPhase.ANALYZING
                    return await self._transition_to_analyzing(session, provider, model)
                
                # Ask next question
                if data.get("next_question"):
                    q = data["next_question"]
                    agent_role = self._get_agent_role(q.get("agent", "requirements"))
                    session.add_message(
                        type=MessageType.QUESTION,
                        agent_role=agent_role,
                        content=q["content"],
                        data={"options": q.get("options", [])},
                    )
            
        except Exception as e:
            session.add_message(
                type=MessageType.SYSTEM,
                content=f"Erreur lors de l'analyse: {str(e)}",
            )
        
        return {"session": session.to_dict(), "needs_response": True}
    
    async def _transition_to_analyzing(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Transition to analysis phase with specialist agents."""
        from app.services.llm_service import llm_service
        from app.prompts.conversation_prompts import (
            DESIGNER_AGENT_PROMPT,
            PHYSICS_AGENT_PROMPT,
            MANUFACTURING_AGENT_PROMPT,
        )
        
        requirements_json = json.dumps(session.requirements.to_dict(), indent=2, ensure_ascii=False)
        
        # Coordinator announces analysis phase
        session.add_message(
            type=MessageType.AGENT,
            agent_role=AgentRole.COORDINATOR,
            content="Parfait ! J'ai maintenant assez d'informations. Laissez-moi consulter nos spécialistes...",
        )
        
        analyses = []
        
        # Designer analysis
        designer_prompt = f"""Exigences du projet:
{requirements_json}

En tant que designer, analyse ces exigences et donne:
1. Recommandations de forme et proportions
2. Suggestions esthétiques
3. Considérations ergonomiques si applicable
4. Questions ou préoccupations

Réponds en JSON:
{{
  "recommendations": ["..."],
  "aesthetic_notes": "...",
  "ergonomic_notes": "...",
  "concerns": ["..."],
  "design_approach": "..."
}}"""
        
        try:
            # Use fast model for agent analysis
            fast_model = get_fast_model(provider)
            designer_response = await llm_service.generate_raw(
                designer_prompt, DESIGNER_AGENT_PROMPT, provider, fast_model, max_tokens=1500
            )
            json_match = re.search(r'\{[\s\S]*\}', designer_response)
            if json_match:
                designer_data = json.loads(json_match.group())
                analyses.append(("designer", designer_data))
        except:
            pass
        
        # Physics analysis (if structural concerns)
        if session.requirements.needs_structural_analysis or session.requirements.expected_load:
            physics_prompt = f"""Exigences du projet:
{requirements_json}

En tant qu'ingénieur en mécanique, analyse:
1. Résistance structurelle requise
2. Points de contrainte potentiels
3. Épaisseur de paroi recommandée
4. Orientation d'impression optimale pour la solidité

Réponds en JSON:
{{
  "structural_assessment": "...",
  "stress_points": ["..."],
  "recommended_wall_thickness": X.X,
  "reinforcement_suggestions": ["..."],
  "print_orientation": "..."
}}"""
            
            try:
                physics_response = await llm_service.generate_raw(
                    physics_prompt, PHYSICS_AGENT_PROMPT, provider, fast_model, max_tokens=1500
                )
                json_match = re.search(r'\{[\s\S]*\}', physics_response)
                if json_match:
                    physics_data = json.loads(json_match.group())
                    analyses.append(("physics", physics_data))
            except:
                pass
        
        # Manufacturing analysis
        manufacturing_prompt = f"""Exigences du projet:
{requirements_json}

En tant qu'expert en fabrication additive, analyse:
1. Imprimabilité de la pièce
2. Supports nécessaires
3. Orientation optimale
4. Paramètres d'impression recommandés
5. Potentiels problèmes (surplombs, ponts, etc.)

Réponds en JSON:
{{
  "printability_score": 8,
  "support_assessment": "...",
  "optimal_orientation": "...",
  "print_settings": {{"layer_height": 0.2, "infill": 20}},
  "potential_issues": ["..."],
  "recommendations": ["..."]
}}"""
        
        try:
            manufacturing_response = await llm_service.generate_raw(
                manufacturing_prompt, MANUFACTURING_AGENT_PROMPT, provider, fast_model, max_tokens=1500
            )
            json_match = re.search(r'\{[\s\S]*\}', manufacturing_response)
            if json_match:
                manufacturing_data = json.loads(json_match.group())
                analyses.append(("manufacturing", manufacturing_data))
        except:
            pass
        
        # Compile and present analysis
        analysis_summary = self._compile_analysis_summary(analyses)
        session.add_message(
            type=MessageType.AGENT,
            agent_role=AgentRole.COORDINATOR,
            content=analysis_summary,
            data={"analyses": dict(analyses)},
        )
        
        # Check if we need user input or can proceed
        concerns = self._extract_concerns(analyses)
        if concerns:
            session.add_message(
                type=MessageType.QUESTION,
                agent_role=AgentRole.COORDINATOR,
                content="Nos spécialistes ont quelques questions avant de continuer:\n\n" + "\n".join(f"• {c}" for c in concerns) + "\n\nVoulez-vous ajuster quelque chose ou puis-je lancer la conception ?",
                data={"options": ["Lancer la conception", "J'ai des modifications"]},
            )
            session.phase = ConversationPhase.REVIEWING
        else:
            session.phase = ConversationPhase.DESIGNING
            return await self._start_design_phase(session, provider, model)
        
        return {"session": session.to_dict(), "needs_response": True}
    
    async def _handle_analyzing_phase(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Handle analysis phase."""
        return await self._transition_to_analyzing(session, provider, model)
    
    async def _handle_reviewing_phase(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Handle review phase - user can modify or approve."""
        last_message = session.messages[-1].content.lower() if session.messages else ""
        
        if any(word in last_message for word in ["lancer", "continuer", "ok", "oui", "génère", "go"]):
            session.phase = ConversationPhase.DESIGNING
            return await self._start_design_phase(session, provider, model)
        else:
            # User wants modifications - go back to gathering
            session.phase = ConversationPhase.GATHERING
            session.add_message(
                type=MessageType.QUESTION,
                agent_role=AgentRole.REQUIREMENTS,
                content="D'accord, quelles modifications souhaitez-vous apporter ?",
            )
            return {"session": session.to_dict(), "needs_response": True}
    
    async def _start_design_phase(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Start the actual design/code generation phase.
        
        Uses the BEST model (Opus 4.5 / GPT-5.2 Pro) for final code generation,
        regardless of what model was used for conversations.
        """
        from app.services.agent_service import agent_service
        
        session.add_message(
            type=MessageType.AGENT,
            agent_role=AgentRole.ENGINEER,
            content="Je commence la conception avec notre meilleur modèle. Cela peut prendre quelques instants...",
        )
        
        # Build comprehensive prompt from requirements
        design_prompt = self._build_design_prompt(session.requirements)
        
        # Get all visual references
        images = session.get_all_images()
        has_visuals = len(images) > 0
        
        # Use BEST model for final code generation (Opus 4.5 / GPT-5.2 Pro)
        best_model = get_best_model(provider)
        
        # Use agent service for generation
        result = await agent_service.generate_with_agents(
            prompt=design_prompt,
            provider=provider,
            model=best_model,
            image_data=images if images else None,
            image_mime_type=None,  # Handled in images list
            context_parts=session.context_parts,
            use_optimization=True,
            use_review=has_visuals,
        )
        
        if result["success"] and result["code"]:
            session.generated_code = result["code"]
            session.phase = ConversationPhase.FINALIZING
            
            session.add_message(
                type=MessageType.CODE,
                agent_role=AgentRole.ENGINEER,
                content="Voici le code généré:",
                data={
                    "code": result["code"],
                    "bounding_box": result["bounding_box"],
                },
            )
            
            # Validator feedback
            if result.get("validation"):
                validation = result["validation"]
                if validation.get("warnings"):
                    session.add_message(
                        type=MessageType.VALIDATION,
                        agent_role=AgentRole.VALIDATOR,
                        content="Quelques notes:\n" + "\n".join(f"• {w}" for w in validation["warnings"]),
                    )
            
            # Suggestions
            if result.get("suggestions"):
                session.add_message(
                    type=MessageType.SUGGESTION,
                    agent_role=AgentRole.COORDINATOR,
                    content="Suggestions d'amélioration:\n" + "\n".join(f"• {s}" for s in result["suggestions"]),
                )
            
            session.add_message(
                type=MessageType.QUESTION,
                agent_role=AgentRole.COORDINATOR,
                content="Le design est prêt ! Souhaitez-vous des modifications ou puis-je finaliser ?",
                data={"options": ["Finaliser", "Modifier", "Recommencer"]},
            )
            
        else:
            session.add_message(
                type=MessageType.AGENT,
                agent_role=AgentRole.ENGINEER,
                content=f"Désolé, j'ai rencontré un problème: {result.get('error', 'Erreur inconnue')}. Voulez-vous réessayer avec des paramètres différents ?",
            )
            session.phase = ConversationPhase.REVIEWING
        
        return {"session": session.to_dict(), "needs_response": True}
    
    async def _handle_designing_phase(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Handle active design phase."""
        return await self._start_design_phase(session, provider, model)
    
    async def _handle_finalizing_phase(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Handle finalizing phase."""
        last_message = session.messages[-1].content.lower() if session.messages else ""
        
        if any(word in last_message for word in ["finaliser", "ok", "oui", "valider", "parfait"]):
            session.phase = ConversationPhase.COMPLETE
            session.add_message(
                type=MessageType.AGENT,
                agent_role=AgentRole.COORDINATOR,
                content="Excellent ! Le design est finalisé. Vous pouvez maintenant l'exécuter et l'exporter.",
            )
            return {"session": session.to_dict(), "needs_response": False, "complete": True}
        
        elif any(word in last_message for word in ["modifier", "change", "ajuste"]):
            session.add_message(
                type=MessageType.QUESTION,
                agent_role=AgentRole.ENGINEER,
                content="Quelles modifications souhaitez-vous ?",
            )
            return {"session": session.to_dict(), "needs_response": True}
        
        elif any(word in last_message for word in ["recommencer", "refaire"]):
            # Reset and start over
            session.phase = ConversationPhase.GATHERING
            session.requirements = DesignRequirements(description=session.requirements.description)
            session.generated_code = None
            session.add_message(
                type=MessageType.QUESTION,
                agent_role=AgentRole.REQUIREMENTS,
                content="D'accord, recommençons. Pouvez-vous me décrire à nouveau ce que vous souhaitez créer ?",
            )
            return {"session": session.to_dict(), "needs_response": True}
        
        else:
            # User is describing modifications
            session.phase = ConversationPhase.DESIGNING
            session.requirements.description += f"\n\nModification demandée: {session.messages[-1].content}"
            return await self._start_design_phase(session, provider, model)
    
    async def _get_coordinator_intro(
        self,
        session: ConversationSession,
        provider: str,
        model: str | None,
    ) -> dict:
        """Get coordinator's introduction."""
        from app.services.llm_service import llm_service
        from app.prompts.conversation_prompts import COORDINATOR_AGENT_PROMPT
        
        context = ""
        if session.requirements.description:
            context = f"\n\nL'utilisateur a déjà indiqué: \"{session.requirements.description}\""
        if session.image_data:
            context += "\n\nL'utilisateur a fourni une image de référence."
        
        prompt = f"""Tu es le coordinateur d'une équipe d'agents IA pour la conception 3D.
{context}

Génère:
1. Un message de bienvenue court et engageant
2. Les premières questions pertinentes à poser

Réponds en JSON:
{{
  "greeting": "Message de bienvenue...",
  "initial_questions": {{
    "content": "Questions à poser...",
    "options": ["Option 1", "Option 2"]  // optionnel, pour les questions à choix
  }}
}}"""
        
        try:
            # Use fast model for agent conversations
            fast_model = get_fast_model(provider)
            response = await llm_service.generate_raw(
                prompt, COORDINATOR_AGENT_PROMPT, provider, fast_model, max_tokens=1000
            )
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback
        return {
            "greeting": "Bonjour ! Je suis votre assistant de conception 3D. Je vais coordonner une équipe d'experts pour vous aider à créer votre pièce.",
            "initial_questions": {
                "content": "Pour commencer, pouvez-vous me décrire ce que vous souhaitez créer ? Quel est l'objectif de cette pièce ?",
                "options": [],
            }
        }
    
    def _build_conversation_history(self, session: ConversationSession) -> str:
        """Build a text representation of conversation history."""
        lines = []
        for msg in session.messages[-10:]:  # Last 10 messages
            role = msg.agent_role.value if msg.agent_role else "user"
            lines.append(f"[{role}]: {msg.content}")
        return "\n".join(lines)
    
    def _update_requirements(self, requirements: DesignRequirements, updates: dict):
        """Update requirements from parsed data."""
        if not updates:
            return
        
        # Basic info
        if "description" in updates:
            requirements.description = updates["description"]
        if "purpose" in updates:
            requirements.purpose = updates["purpose"]
        
        # Dimensions
        dims = updates.get("dimensions", {})
        if dims:
            requirements.dimensions_specified = dims.get("specified", requirements.dimensions_specified)
            requirements.length = dims.get("length", requirements.length)
            requirements.width = dims.get("width", requirements.width)
            requirements.height = dims.get("height", requirements.height)
        
        # Physical
        phys = updates.get("physical", {})
        if phys:
            requirements.needs_structural_analysis = phys.get("needs_structural_analysis", requirements.needs_structural_analysis)
            requirements.expected_load = phys.get("expected_load", requirements.expected_load)
            requirements.material = phys.get("material", requirements.material)
            requirements.wall_thickness = phys.get("wall_thickness", requirements.wall_thickness)
        
        # Aesthetics
        aest = updates.get("aesthetics", {})
        if aest:
            requirements.style = aest.get("style", requirements.style)
            requirements.finish = aest.get("finish", requirements.finish)
            requirements.has_fillets = aest.get("has_fillets", requirements.has_fillets)
            requirements.fillet_radius = aest.get("fillet_radius", requirements.fillet_radius)
        
        # Features
        if "features" in updates:
            requirements.features = updates["features"]
        
        # Manufacturing
        mfg = updates.get("manufacturing", {})
        if mfg:
            requirements.printer_type = mfg.get("printer_type", requirements.printer_type)
            requirements.layer_height = mfg.get("layer_height", requirements.layer_height)
            requirements.needs_supports = mfg.get("needs_supports", requirements.needs_supports)
            requirements.orientation_preference = mfg.get("orientation_preference", requirements.orientation_preference)
        
        # Assembly
        asm = updates.get("assembly", {})
        if asm:
            requirements.is_part_of_assembly = asm.get("is_part_of_assembly", requirements.is_part_of_assembly)
            requirements.mating_parts = asm.get("mating_parts", requirements.mating_parts)
            requirements.tolerances = asm.get("tolerances", requirements.tolerances)
    
    def _get_agent_role(self, agent_name: str) -> AgentRole:
        """Convert agent name string to AgentRole."""
        mapping = {
            "coordinator": AgentRole.COORDINATOR,
            "requirements": AgentRole.REQUIREMENTS,
            "designer": AgentRole.DESIGNER,
            "engineer": AgentRole.ENGINEER,
            "physics": AgentRole.PHYSICS,
            "manufacturing": AgentRole.MANUFACTURING,
            "validator": AgentRole.VALIDATOR,
        }
        return mapping.get(agent_name.lower(), AgentRole.REQUIREMENTS)
    
    def _compile_analysis_summary(self, analyses: list[tuple[str, dict]]) -> str:
        """Compile analysis results into a summary."""
        parts = ["Voici l'analyse de notre équipe:\n"]
        
        for agent, data in analyses:
            if agent == "designer":
                parts.append("**Designer:**")
                if data.get("design_approach"):
                    parts.append(f"  Approche: {data['design_approach']}")
                if data.get("recommendations"):
                    parts.append("  Recommandations: " + ", ".join(data["recommendations"][:3]))
            
            elif agent == "physics":
                parts.append("**Ingénieur Mécanique:**")
                if data.get("structural_assessment"):
                    parts.append(f"  Analyse: {data['structural_assessment']}")
                if data.get("recommended_wall_thickness"):
                    parts.append(f"  Épaisseur recommandée: {data['recommended_wall_thickness']}mm")
            
            elif agent == "manufacturing":
                parts.append("**Expert Fabrication:**")
                if data.get("printability_score"):
                    parts.append(f"  Score d'imprimabilité: {data['printability_score']}/10")
                if data.get("optimal_orientation"):
                    parts.append(f"  Orientation: {data['optimal_orientation']}")
                if data.get("potential_issues"):
                    parts.append("  Points d'attention: " + ", ".join(data["potential_issues"][:2]))
        
        return "\n".join(parts)
    
    def _extract_concerns(self, analyses: list[tuple[str, dict]]) -> list[str]:
        """Extract concerns/questions from analyses."""
        concerns = []
        for agent, data in analyses:
            if data.get("concerns"):
                concerns.extend(data["concerns"][:2])
            if data.get("potential_issues"):
                concerns.extend(data["potential_issues"][:2])
        return concerns[:5]  # Max 5 concerns
    
    def _build_design_prompt(self, req: DesignRequirements) -> str:
        """Build a comprehensive design prompt from requirements."""
        parts = [f"Crée une pièce 3D: {req.description}"]
        
        if req.purpose:
            parts.append(f"Usage: {req.purpose}")
        
        if req.dimensions_specified:
            dims = []
            if req.length:
                dims.append(f"longueur={req.length}mm")
            if req.width:
                dims.append(f"largeur={req.width}mm")
            if req.height:
                dims.append(f"hauteur={req.height}mm")
            if dims:
                parts.append(f"Dimensions: {', '.join(dims)}")
        
        if req.wall_thickness:
            parts.append(f"Épaisseur de paroi: {req.wall_thickness}mm")
        
        if req.features:
            parts.append(f"Features: {', '.join(req.features)}")
        
        if req.style:
            parts.append(f"Style: {req.style}")
        
        if req.material != "PLA":
            parts.append(f"Matériau: {req.material}")
        
        if req.expected_load:
            parts.append(f"Charge attendue: {req.expected_load}kg")
        
        if req.is_part_of_assembly:
            parts.append(f"Fait partie d'un assemblage avec: {', '.join(req.mating_parts)}")
        
        return "\n".join(parts)


# Singleton instance
conversation_service = ConversationService()
