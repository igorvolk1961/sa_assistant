import uuid

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    user_id: uuid.UUID | None = None
    last_name: str | None = Field(default=None, max_length=100)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)


class EmployeeOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    last_name: str | None
    first_name: str | None
    middle_name: str | None


class LinkUserRequest(BaseModel):
    user_id: uuid.UUID | None = None


class PositionAssignment(BaseModel):
    position_id: uuid.UUID


class StakeholderCreate(BaseModel):
    position_id: uuid.UUID
    user_id: uuid.UUID | None = None
    last_name: str | None = Field(default=None, max_length=100)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    organization: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class StakeholderOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    position_id: uuid.UUID
    user_id: uuid.UUID | None
    last_name: str | None
    first_name: str | None
    middle_name: str | None
    organization: str | None
    notes: str | None
