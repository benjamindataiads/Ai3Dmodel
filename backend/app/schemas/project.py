from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ProjectCreate(ProjectBase):
    section_id: UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    section_id: UUID | None = None
    position: int | None = None


class PartSummary(BaseModel):
    id: UUID
    name: str
    status: str
    
    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    id: UUID
    section_id: UUID | None = None
    position: int = 0
    created_at: datetime
    updated_at: datetime
    parts: list[PartSummary] = []
    
    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Summary for use in section lists"""
    id: UUID
    name: str
    description: str | None
    position: int = 0
    created_at: datetime
    updated_at: datetime
    parts_count: int = 0
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    section_id: UUID | None = None
    position: int = 0
    created_at: datetime
    updated_at: datetime
    parts_count: int = 0
    
    class Config:
        from_attributes = True
