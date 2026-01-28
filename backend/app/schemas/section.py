from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class SectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: str | None = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    color: str | None = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    position: int | None = None


class SectionResponse(SectionBase):
    id: UUID
    position: int
    projects_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionWithProjects(SectionResponse):
    projects: list["ProjectSummary"] = []


# Import at the end to avoid circular imports
from app.schemas.project import ProjectSummary
SectionWithProjects.model_rebuild()
