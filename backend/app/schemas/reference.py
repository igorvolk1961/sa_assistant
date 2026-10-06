import uuid

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ----------------------------- Input -----------------------------
class PositionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=50)
    representatives: str | None = None
    influence: str | None = Field(default=None, max_length=200)
    sort_order: int = 0
    assignable_as_position: bool = True
    usable_as_stakeholder_type: bool = True


class PositionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=50)
    representatives: str | None = None
    influence: str | None = Field(default=None, max_length=200)
    sort_order: int | None = None
    assignable_as_position: bool | None = None
    usable_as_stakeholder_type: bool | None = None


class MandatoryQuestionCreate(BaseModel):
    position_id: uuid.UUID
    text: str = Field(min_length=1)
    is_mandatory: bool = True
    sort_order: int = 0


class MandatoryQuestionUpdate(BaseModel):
    text: str | None = None
    is_mandatory: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class NfrTypeCreate(BaseModel):
    code: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None


class LlmModelCreate(BaseModel):
    provider: str | None = Field(default=None, max_length=100)
    model_code: str | None = Field(default=None, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    is_default: bool = False
    params: dict | None = None


class SttModelCreate(BaseModel):
    provider: str | None = Field(default=None, max_length=100)
    model_code: str | None = Field(default=None, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    is_default: bool = False
    supports_streaming: bool | None = None
    supports_diarization: bool | None = None
    session_limit_sec: int | None = None


class PromptTemplateCreate(BaseModel):
    purpose: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    template: str | None = None
    is_system: bool = False


# ----------------------------- Output -----------------------------
class PositionOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    category: str | None
    representatives: str | None
    influence: str | None
    sort_order: int
    assignable_as_position: bool
    usable_as_stakeholder_type: bool
    is_system: bool


class MandatoryQuestionOut(ORMModel):
    id: uuid.UUID
    position_id: uuid.UUID
    text: str
    is_mandatory: bool
    sort_order: int
    is_active: bool


class NfrTypeOut(ORMModel):
    id: uuid.UUID
    code: str | None
    name: str | None
    description: str | None


class LlmModelOut(ORMModel):
    id: uuid.UUID
    provider: str | None
    model_code: str | None
    display_name: str | None
    is_default: bool
    params: dict | None


class SttModelOut(ORMModel):
    id: uuid.UUID
    provider: str | None
    model_code: str | None
    display_name: str | None
    is_default: bool
    supports_streaming: bool | None
    supports_diarization: bool | None
    session_limit_sec: int | None


class PromptTemplateOut(ORMModel):
    id: uuid.UUID
    purpose: str | None
    name: str | None
    template: str | None
    is_system: bool
