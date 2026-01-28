from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float
    y: float
    z: float


class Parameter(BaseModel):
    name: str
    value: float
    unit: str = "mm"
    line: int | None = None
    min_value: float | None = None
    max_value: float | None = None


class PartBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PartCreate(PartBase):
    code: str | None = None
    prompt: str | None = None


class PartUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    prompt: str | None = None


class PartResponse(PartBase):
    id: UUID
    project_id: UUID
    code: str | None
    prompt: str | None
    parameters: list[Parameter] | None
    bounding_box: BoundingBox | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContextPart(BaseModel):
    name: str
    code: str


class PartGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    provider: Literal["openai", "anthropic"] | None = None
    model: str | None = None  # Specific model to use (e.g., "gpt-4o", "claude-opus-4-20250514")
    existing_code: str | None = None  # If provided, AI will modify this code
    context_parts: list[ContextPart] | None = None  # Other parts for context


class PartParametersUpdate(BaseModel):
    parameters: dict[str, float]


class PartValidateRequest(BaseModel):
    build_volume: BoundingBox


class PartValidateResponse(BaseModel):
    fits_build_volume: bool
    part_dimensions: BoundingBox
    build_volume: BoundingBox
    overflow: BoundingBox
    suggestions: list[str]
