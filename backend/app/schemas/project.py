import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ProjectStatus, RoleCode


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    code: str | None = Field(default=None, max_length=100)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    code: str | None = Field(default=None, max_length=100)
    description: str | None = None


class ProjectOut(ORMModel):
    id: uuid.UUID
    code: str | None
    name: str
    description: str | None
    status: ProjectStatus
    created_by: uuid.UUID | None
    created_at: datetime
    closed_at: datetime | None


class MemberAdd(BaseModel):
    user_id: uuid.UUID
    role: RoleCode


class MemberRolesUpdate(BaseModel):
    roles: list[RoleCode]


class MemberOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    is_owner: bool
    joined_at: datetime
    roles: list[RoleCode]


class TransferAnalystRequest(BaseModel):
    user_id: uuid.UUID
