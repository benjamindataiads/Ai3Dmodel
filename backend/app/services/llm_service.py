from typing import Literal
import openai
import anthropic

from app.config import settings
from app.prompts.cadquery_system import CADQUERY_SYSTEM_PROMPT, CADQUERY_EDIT_PROMPT, CADQUERY_CONTEXT_PROMPT


# Available models per provider
OPENAI_MODELS = {
    "gpt-5.2": "GPT-5.2 (Best)",
    "gpt-5.2-pro": "GPT-5.2 Pro",
    "gpt-5-mini": "GPT-5 Mini",
    "gpt-5-nano": "GPT-5 Nano (Fast)",
    "gpt-4.1": "GPT-4.1",
    "gpt-4o": "GPT-4o",
    "o4-mini": "o4 Mini (Reasoning)",
}

ANTHROPIC_MODELS = {
    "claude-sonnet-4-5-20250929": "Sonnet 4.5 (Balanced)",
    "claude-opus-4-5-20251101": "Opus 4.5 (Best)",
    "claude-haiku-4-5-20251001": "Haiku 4.5 (Fast)",
}

DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"


class LLMService:
    """Unified service for LLM code generation."""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
    
    def _get_openai_client(self):
        if not self.openai_client:
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        return self.openai_client
    
    def _get_anthropic_client(self):
        if not self.anthropic_client:
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self.anthropic_client
    
    async def generate_cad_code(
        self,
        prompt: str,
        provider: Literal["openai", "anthropic"],
        existing_code: str | None = None,
        context_parts: list[tuple[str, str]] | None = None,
        model: str | None = None,
    ) -> str:
        """Generate CadQuery code from natural language prompt."""
        if provider == "openai":
            return await self._generate_with_openai(prompt, existing_code, context_parts, model)
        elif provider == "anthropic":
            return await self._generate_with_anthropic(prompt, existing_code, context_parts, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _build_prompt(
        self, 
        prompt: str, 
        existing_code: str | None, 
        context_parts: list[tuple[str, str]] | None
    ) -> tuple[str, str]:
        """Build system and user prompts based on mode."""
        system_prompt = CADQUERY_SYSTEM_PROMPT
        user_prompt = prompt
        
        # Add context parts if provided
        context_section = ""
        if context_parts:
            system_prompt = CADQUERY_CONTEXT_PROMPT
            context_section = "## Pièces existantes dans le projet\n\n"
            for name, code in context_parts:
                context_section += f"### {name}\n```python\n{code}\n```\n\n"
        
        if existing_code:
            # Edit mode
            if not context_parts:
                system_prompt = CADQUERY_EDIT_PROMPT
            user_prompt = f"""{context_section}Code actuel à modifier:
```python
{existing_code}
```

Modifications demandées: {prompt}"""
        elif context_parts:
            # New part with context
            user_prompt = f"""{context_section}Nouvelle pièce à créer: {prompt}"""
        
        return system_prompt, user_prompt
    
    async def _generate_with_openai(
        self, 
        prompt: str, 
        existing_code: str | None = None,
        context_parts: list[tuple[str, str]] | None = None,
        model: str | None = None
    ) -> str:
        """Generate code using OpenAI."""
        client = self._get_openai_client()
        
        system_prompt, user_prompt = self._build_prompt(prompt, existing_code, context_parts)
        model_to_use = model if model and model in OPENAI_MODELS else DEFAULT_OPENAI_MODEL
        
        response = await client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        
        content = response.choices[0].message.content
        return self._extract_code(content)
    
    async def _generate_with_anthropic(
        self, 
        prompt: str, 
        existing_code: str | None = None,
        context_parts: list[tuple[str, str]] | None = None,
        model: str | None = None
    ) -> str:
        """Generate code using Anthropic Claude."""
        client = self._get_anthropic_client()
        
        system_prompt, user_prompt = self._build_prompt(prompt, existing_code, context_parts)
        model_to_use = model if model and model in ANTHROPIC_MODELS else DEFAULT_ANTHROPIC_MODEL
        
        response = await client.messages.create(
            model=model_to_use,
            max_tokens=4000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        
        content = response.content[0].text
        return self._extract_code(content)
    
    def _extract_code(self, content: str) -> str:
        """Extract Python code from LLM response."""
        # Try to extract from code block
        if "```python" in content:
            start = content.find("```python") + len("```python")
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        
        if "```" in content:
            start = content.find("```") + 3
            # Skip language identifier if present
            newline = content.find("\n", start)
            if newline > start and newline - start < 20:
                start = newline + 1
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        
        # Return as-is if no code blocks found
        return content.strip()
    
    async def generate_raw(
        self,
        user_prompt: str,
        system_prompt: str,
        provider: Literal["openai", "anthropic"],
        model: str | None = None,
        max_tokens: int = 8000,
    ) -> str:
        """Generate raw response from LLM (no code extraction)."""
        if provider == "openai":
            client = self._get_openai_client()
            model_to_use = model if model and model in OPENAI_MODELS else DEFAULT_OPENAI_MODEL
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        
        elif provider == "anthropic":
            client = self._get_anthropic_client()
            model_to_use = model if model and model in ANTHROPIC_MODELS else DEFAULT_ANTHROPIC_MODEL
            response = await client.messages.create(
                model=model_to_use,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.content[0].text
        
        else:
            raise ValueError(f"Unknown provider: {provider}")


llm_service = LLMService()
