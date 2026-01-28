from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel


class VersionResponse(BaseModel):
    id: UUID
    part_id: UUID
    code: str | None
    prompt: str | None
    parameters: dict[str, Any] | None
    bounding_box: dict[str, Any] | None
    status: str
    error_message: str | None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class VersionSummary(BaseModel):
    """Lightweight version for listing."""
    id: UUID
    source: str
    status: str
    created_at: datetime
    has_code: bool = False

    class Config:
        from_attributes = True
