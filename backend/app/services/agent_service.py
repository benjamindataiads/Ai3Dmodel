"""
Multi-agent system for intelligent 3D model design and optimization.

Agents:
- Orchestrator: Coordinates workflow and decides which agents to invoke
- Design Agent: Generates initial CadQuery code from description/image
- Validation Agent: Checks for errors and 3D printing compatibility
- Optimization Agent: Improves design for 3D printing
- Review Agent: Compares result to original intent using vision

Model strategy:
- Fast models (Haiku/Nano) for validation, analysis, and review
- Best models (Opus/GPT-5.2 Pro) for actual code generation
"""
import asyncio
import base64
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from app.config import settings
from app.services.llm_service import llm_service
from app.services.cad_service import cad_service
from app.services.validation_service import code_validator


def get_fast_model(provider: str) -> str:
    """Get the fast model for validation/analysis (cheap & fast)."""
    if provider == "anthropic":
        return "claude-haiku-4-5-20251001"
    return "gpt-5-nano"


def get_best_model(provider: str) -> str:
    """Get the best model for code generation (most capable)."""
    if provider == "anthropic":
        return "claude-opus-4-5-20251101"
    return "gpt-5.2-pro"


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    DESIGN = "design"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    REVIEW = "review"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    role: AgentRole
    content: str
    data: dict = field(default_factory=dict)


@dataclass
class DesignContext:
    """Context for the design process."""
    original_prompt: str
    # Support single image (legacy) or multiple images
    image_data: str | list[tuple[str, str]] | None = None  # Single base64 or list of (data, mime_type)
    image_mime_type: str | None = None  # Only used for single image
    existing_code: str | None = None
    context_parts: list[tuple[str, str]] | None = None
    printer_settings: dict | None = None
    
    # Generated during process
    code: str | None = None
    validation_result: dict | None = None
    optimization_suggestions: list[str] = field(default_factory=list)
    bounding_box: dict | None = None
    iterations: int = 0
    max_iterations: int = 3
    messages: list[AgentMessage] = field(default_factory=list)
    
    def has_images(self) -> bool:
        """Check if context has any images."""
        if isinstance(self.image_data, list):
            return len(self.image_data) > 0
        return self.image_data is not None
    
    def get_images_for_vision(self) -> list[tuple[str, str]] | None:
        """Get images in format suitable for vision API."""
        if isinstance(self.image_data, list):
            return self.image_data if self.image_data else None
        elif self.image_data:
            return [(self.image_data, self.image_mime_type or "image/jpeg")]
        return None


class AgentService:
    """Multi-agent system for CAD generation and optimization."""
    
    def __init__(self):
        self.max_retries = 3
    
    async def generate_with_agents(
        self,
        prompt: str,
        provider: Literal["openai", "anthropic"],
        model: str | None = None,
        image_data: str | list[tuple[str, str]] | None = None,
        image_mime_type: str | None = None,
        existing_code: str | None = None,
        context_parts: list[tuple[str, str]] | None = None,
        printer_settings: dict | None = None,
        use_optimization: bool = True,
        use_review: bool = True,
    ) -> dict:
        """
        Run the multi-agent pipeline to generate optimized CadQuery code.
        
        Returns:
            dict with keys: code, bounding_box, suggestions, iterations, messages
        """
        context = DesignContext(
            original_prompt=prompt,
            image_data=image_data,
            image_mime_type=image_mime_type,
            existing_code=existing_code,
            context_parts=context_parts,
            printer_settings=printer_settings or self._default_printer_settings(),
        )
        
        # Step 1: Design Agent generates initial code
        context = await self._run_design_agent(context, provider, model)
        
        if not context.code:
            return self._build_response(context, success=False, error="Design agent failed to generate code")
        
        # Step 2: Validation Agent checks the code
        context = await self._run_validation_agent(context, provider, model)
        
        # Step 3: If validation failed, retry with fixes
        while not context.validation_result.get("valid") and context.iterations < context.max_iterations:
            context.iterations += 1
            context = await self._run_design_agent(
                context, provider, model, 
                fix_errors=context.validation_result.get("errors", [])
            )
            context = await self._run_validation_agent(context, provider, model)
        
        # Step 4: Optimization Agent (if enabled and validation passed)
        if use_optimization and context.validation_result.get("valid"):
            context = await self._run_optimization_agent(context, provider, model)
        
        # Step 5: Review Agent (if enabled and we have an image)
        if use_review and context.image_data and context.validation_result.get("valid"):
            context = await self._run_review_agent(context, provider, model)
        
        return self._build_response(context, success=context.validation_result.get("valid", False))
    
    async def _run_design_agent(
        self,
        context: DesignContext,
        provider: str,
        model: str | None,
        fix_errors: list[str] | None = None,
    ) -> DesignContext:
        """Design Agent: Generate CadQuery code from description/image."""
        from app.prompts.agent_prompts import DESIGN_AGENT_PROMPT, DESIGN_WITH_IMAGE_PROMPT
        
        # Build the user prompt
        user_prompt_parts = []
        
        if context.has_images():
            images = context.get_images_for_vision()
            if images and len(images) > 1:
                user_prompt_parts.append(f"J'ai fourni {len(images)} images/dessins de référence pour guider la conception.")
            else:
                user_prompt_parts.append("J'ai fourni une image de référence pour guider la conception.")
        
        user_prompt_parts.append(f"Description: {context.original_prompt}")
        
        if context.existing_code:
            user_prompt_parts.append(f"\nCode existant à modifier:\n```python\n{context.existing_code}\n```")
        
        if context.context_parts:
            user_prompt_parts.append("\nPièces existantes dans le projet:")
            for name, code in context.context_parts:
                user_prompt_parts.append(f"\n### {name}\n```python\n{code}\n```")
        
        if fix_errors:
            user_prompt_parts.append(f"\n\n⚠️ ERREURS À CORRIGER:\n" + "\n".join(f"- {e}" for e in fix_errors))
            user_prompt_parts.append("\nGénère une version corrigée du code.")
        
        user_prompt = "\n".join(user_prompt_parts)
        system_prompt = DESIGN_WITH_IMAGE_PROMPT if context.has_images() else DESIGN_AGENT_PROMPT
        
        try:
            images = context.get_images_for_vision()
            if images:
                # Use vision-capable generation
                code = await self._generate_with_vision(
                    user_prompt,
                    system_prompt,
                    images,
                    None,  # mime_type handled in images list
                    provider,
                    model,
                )
            else:
                code = await llm_service.generate_cad_code(
                    user_prompt,
                    provider,
                    existing_code=None,  # Already included in prompt
                    context_parts=None,  # Already included in prompt
                    model=model,
                    validate=True,
                    auto_correct=True,
                )
            
            context.code = code
            context.messages.append(AgentMessage(
                role=AgentRole.DESIGN,
                content="Code generated" + (" with fixes" if fix_errors else ""),
                data={"code_length": len(code) if code else 0}
            ))
            
        except Exception as e:
            context.messages.append(AgentMessage(
                role=AgentRole.DESIGN,
                content=f"Error: {str(e)}",
                data={"error": str(e)}
            ))
        
        return context
    
    async def _run_validation_agent(
        self,
        context: DesignContext,
        provider: str,
        model: str | None,
    ) -> DesignContext:
        """Validation Agent: Check code for errors and printability."""
        from app.prompts.agent_prompts import VALIDATION_AGENT_PROMPT
        
        if not context.code:
            context.validation_result = {"valid": False, "errors": ["No code to validate"]}
            return context
        
        errors = []
        warnings = []
        
        # Step 1: Static validation
        static_result = code_validator.validate(context.code)
        if static_result.corrected_code:
            context.code = static_result.corrected_code
        errors.extend(static_result.errors)
        warnings.extend(static_result.warnings)
        
        # Step 2: Execute code to validate
        try:
            exec_result = await cad_service.execute_code(context.code)
            
            if exec_result.success:
                context.bounding_box = exec_result.bounding_box
                
                # Check printability
                printability = self._check_printability(
                    exec_result.bounding_box,
                    context.printer_settings
                )
                if not printability["fits"]:
                    warnings.append(f"Part exceeds build volume: {printability['overflow']}")
                    
            else:
                errors.append(f"Execution error: {exec_result.error}")
                
        except Exception as e:
            errors.append(f"Execution failed: {str(e)}")
        
        # Step 3: LLM-based code review for potential issues
        if not errors:
            try:
                review_prompt = f"""Analyse ce code CadQuery pour détecter des problèmes potentiels:

```python
{context.code}
```

Vérifie:
1. Opérations géométriques risquées (loft, sweep complexes)
2. Fillets/chamfers potentiellement problématiques
3. Dimensions incohérentes
4. Problèmes d'imprimabilité 3D (surplombs, parois fines)

Réponds en JSON: {{"issues": [...], "suggestions": [...]}}"""

                # Use fast model for validation analysis
                fast_model = get_fast_model(provider)
                review_response = await llm_service.generate_raw(
                    review_prompt,
                    VALIDATION_AGENT_PROMPT,
                    provider,
                    fast_model,
                    max_tokens=1000,
                )
                
                # Extract JSON
                json_match = re.search(r'\{[\s\S]*\}', review_response)
                if json_match:
                    review_data = json.loads(json_match.group())
                    warnings.extend(review_data.get("issues", []))
                    context.optimization_suggestions.extend(review_data.get("suggestions", []))
                    
            except Exception:
                pass  # Non-critical, continue
        
        context.validation_result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
        
        context.messages.append(AgentMessage(
            role=AgentRole.VALIDATION,
            content="Valid" if not errors else f"Invalid: {len(errors)} errors",
            data=context.validation_result
        ))
        
        return context
    
    async def _run_optimization_agent(
        self,
        context: DesignContext,
        provider: str,
        model: str | None,
    ) -> DesignContext:
        """Optimization Agent: Improve design for 3D printing."""
        from app.prompts.agent_prompts import OPTIMIZATION_AGENT_PROMPT
        
        if not context.code or not context.validation_result.get("valid"):
            return context
        
        optimization_prompt = f"""Code CadQuery actuel:
```python
{context.code}
```

Paramètres imprimante:
- Volume: {context.printer_settings.get('build_volume', {})}
- Épaisseur couche: {context.printer_settings.get('layer_height', 0.2)}mm
- Épaisseur paroi min: {context.printer_settings.get('min_wall_thickness', 1.2)}mm

Dimensions actuelles: {context.bounding_box}

Suggestions existantes: {context.optimization_suggestions}

Optimise le code pour l'impression 3D si nécessaire. Si le code est déjà optimal, retourne-le tel quel.
Assure-toi que:
1. Les parois sont assez épaisses (>= {context.printer_settings.get('min_wall_thickness', 1.2)}mm)
2. Les surplombs sont minimisés ou < 45°
3. Les détails sont imprimables à {context.printer_settings.get('layer_height', 0.2)}mm de résolution

Retourne UNIQUEMENT le code Python optimisé."""

        try:
            # Use fast model for optimization - just tweaking existing code
            fast_model = get_fast_model(provider)
            optimized_code = await llm_service.generate_raw(
                optimization_prompt,
                OPTIMIZATION_AGENT_PROMPT,
                provider,
                fast_model,
            )
            
            # Extract code
            extracted = self._extract_code(optimized_code)
            if extracted:
                # Validate the optimized code
                exec_result = await cad_service.execute_code(extracted)
                if exec_result.success:
                    context.code = extracted
                    context.bounding_box = exec_result.bounding_box
                    context.messages.append(AgentMessage(
                        role=AgentRole.OPTIMIZATION,
                        content="Code optimized for 3D printing",
                        data={"bounding_box": exec_result.bounding_box}
                    ))
                else:
                    context.messages.append(AgentMessage(
                        role=AgentRole.OPTIMIZATION,
                        content="Optimization skipped - optimized code had errors",
                        data={"error": exec_result.error}
                    ))
            
        except Exception as e:
            context.messages.append(AgentMessage(
                role=AgentRole.OPTIMIZATION,
                content=f"Optimization failed: {str(e)}",
                data={"error": str(e)}
            ))
        
        return context
    
    async def _run_review_agent(
        self,
        context: DesignContext,
        provider: str,
        model: str | None,
    ) -> DesignContext:
        """Review Agent: Compare generated model to original image/intent."""
        from app.prompts.agent_prompts import REVIEW_AGENT_PROMPT
        
        # This would ideally render the 3D model and compare with the input image
        # For now, we do a description-based comparison
        
        review_prompt = f"""Prompt original: {context.original_prompt}

Code généré:
```python
{context.code}
```

Dimensions finales: {context.bounding_box}

Évalue si le code correspond bien à la demande originale.
Note de 1 à 10 et explique les différences potentielles.

Réponds en JSON: {{"score": X, "matches": true/false, "differences": [...], "suggestions": [...]}}"""

        try:
            # Use fast model for review analysis
            fast_model = get_fast_model(provider)
            
            if context.image_data:
                # Use vision to compare with original image
                review_response = await self._generate_with_vision(
                    review_prompt + "\n\nCompare également avec l'image de référence fournie.",
                    REVIEW_AGENT_PROMPT,
                    context.image_data,
                    context.image_mime_type,
                    provider,
                    fast_model,
                )
            else:
                review_response = await llm_service.generate_raw(
                    review_prompt,
                    REVIEW_AGENT_PROMPT,
                    provider,
                    fast_model,
                    max_tokens=1000,
                )
            
            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', review_response)
            if json_match:
                review_data = json.loads(json_match.group())
                context.messages.append(AgentMessage(
                    role=AgentRole.REVIEW,
                    content=f"Score: {review_data.get('score', 'N/A')}/10",
                    data=review_data
                ))
                
                # Add any new suggestions
                context.optimization_suggestions.extend(review_data.get("suggestions", []))
                
        except Exception as e:
            context.messages.append(AgentMessage(
                role=AgentRole.REVIEW,
                content=f"Review failed: {str(e)}",
                data={"error": str(e)}
            ))
        
        return context
    
    async def _generate_with_vision(
        self,
        user_prompt: str,
        system_prompt: str,
        image_data: str | list[tuple[str, str]],
        image_mime_type: str | None,
        provider: str,
        model: str | None,
    ) -> str:
        """Generate response using vision-capable models.
        
        Args:
            image_data: Either a single base64 string, or a list of (data, mime_type) tuples
        """
        import openai
        import anthropic
        
        # Normalize to list of (data, mime_type) tuples
        if isinstance(image_data, str):
            images = [(image_data, image_mime_type or "image/jpeg")]
        else:
            images = image_data
        
        if provider == "openai":
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Build content with multiple images
            content_parts = [{"type": "text", "text": user_prompt}]
            for data, mime_type in images:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{data}"
                    }
                })
            
            response = await client.chat.completions.create(
                model=model or "gpt-4o",  # Vision-capable model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_parts}
                ],
                max_tokens=4000,
                temperature=0.2,
            )
            content = response.choices[0].message.content
            
        elif provider == "anthropic":
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            
            # Build content with multiple images (images first, then text)
            content_parts = []
            for data, mime_type in images:
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": data,
                    }
                })
            content_parts.append({"type": "text", "text": user_prompt})
            
            response = await client.messages.create(
                model=model or "claude-sonnet-4-5-20250929",
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": content_parts}],
            )
            content = response.content[0].text
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        return self._extract_code(content) or content
    
    def _extract_code(self, content: str) -> str | None:
        """Extract Python code from response."""
        if "```python" in content:
            start = content.find("```python") + len("```python")
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        
        if "```" in content:
            start = content.find("```") + 3
            newline = content.find("\n", start)
            if newline > start and newline - start < 20:
                start = newline + 1
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        
        return None
    
    def _check_printability(self, bounding_box: dict, printer_settings: dict) -> dict:
        """Check if part fits in build volume."""
        build_volume = printer_settings.get("build_volume", {"x": 220, "y": 220, "z": 250})
        
        overflow = {
            "x": max(0, bounding_box.get("x", 0) - build_volume["x"]),
            "y": max(0, bounding_box.get("y", 0) - build_volume["y"]),
            "z": max(0, bounding_box.get("z", 0) - build_volume["z"]),
        }
        
        fits = overflow["x"] == 0 and overflow["y"] == 0 and overflow["z"] == 0
        
        return {"fits": fits, "overflow": overflow}
    
    def _default_printer_settings(self) -> dict:
        """Default printer settings."""
        return {
            "build_volume": {"x": 220, "y": 220, "z": 250},
            "layer_height": 0.2,
            "min_wall_thickness": 1.2,
            "nozzle_diameter": 0.4,
        }
    
    def _build_response(self, context: DesignContext, success: bool, error: str | None = None) -> dict:
        """Build the final response."""
        return {
            "success": success,
            "code": context.code,
            "bounding_box": context.bounding_box,
            "validation": context.validation_result,
            "suggestions": context.optimization_suggestions,
            "iterations": context.iterations,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "data": msg.data,
                }
                for msg in context.messages
            ],
            "error": error,
        }


# Singleton instance
agent_service = AgentService()
