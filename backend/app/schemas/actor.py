import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    user_id: uuid.UUID | None = None
    last_name: str | None = Field(default=None, max_length=100)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)

    @field_validator("user_id", mode="before")
    @classmethod
    def _blank_user_id(cls, value: object) -> object:
        return None if value == "" else value


class EmployeeOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    last_name: str | None
    first_name: str | None
    middle_name: str | None


class LinkUserRequest(BaseModel):
    user_id: uuid.UUID | None = None

    @field_validator("user_id", mode="before")
    @classmethod
    def _blank_user_id(cls, value: object) -> object:
        return None if value == "" else value


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

    @field_validator("user_id", mode="before")
    @classmethod
    def _blank_user_id(cls, value: object) -> object:
        return None if value == "" else value


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
