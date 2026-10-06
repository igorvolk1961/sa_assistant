import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ImplementationStatus, Importance, PriorityMoscow, RequirementType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequirementCreate(BaseModel):
    type: RequirementType
    title: str = Field(min_length=1, max_length=300)
    stakeholder_id: uuid.UUID | None = None
    stakeholder_type_id: uuid.UUID | None = None
    code: str | None = Field(default=None, max_length=50)
    epic: str | None = Field(default=None, max_length=300)
    short_description: str | None = None
    description: str | None = None
    acceptance_criteria: str | None = None
    nfr_type_id: uuid.UUID | None = None
    importance: Importance = Importance.medium
    priority_moscow: PriorityMoscow | None = None
    implementation_status: ImplementationStatus | None = None
    source: str | None = Field(default=None, max_length=100)


class RequirementUpdate(BaseModel):
    stakeholder_id: uuid.UUID | None = None
    stakeholder_type_id: uuid.UUID | None = None
    code: str | None = Field(default=None, max_length=50)
    epic: str | None = Field(default=None, max_length=300)
    type: RequirementType | None = None
    title: str | None = Field(default=None, max_length=300)
    short_description: str | None = None
    description: str | None = None
    acceptance_criteria: str | None = None
    nfr_type_id: uuid.UUID | None = None
    importance: Importance | None = None
    priority_moscow: PriorityMoscow | None = None
    implementation_status: ImplementationStatus | None = None
    status: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)


class RequirementOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    stakeholder_id: uuid.UUID | None
    stakeholder_type_id: uuid.UUID | None
    code: str | None
    epic: str | None
    type: RequirementType
    title: str
    short_description: str | None
    description: str | None
    acceptance_criteria: str | None
    nfr_type_id: uuid.UUID | None
    importance: Importance
    priority_moscow: PriorityMoscow | None
    implementation_status: ImplementationStatus | None
    status: str | None
    source: str | None
    created_by: uuid.UUID | None
    created_at: datetime


class ArtifactCreate(BaseModel):
    type: str = Field(max_length=50)
    content: dict
    meeting_id: uuid.UUID | None = None
    source: str = Field(default="manual", max_length=20)


class ArtifactUpdate(BaseModel):
    content: dict | None = None


class ArtifactOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    meeting_id: uuid.UUID | None
    type: str
    content: dict
    source: str
    version: int
    created_by: uuid.UUID | None
    created_at: datetime
