import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Importance, TaskStatus, TaskType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    requirement_id: uuid.UUID
    type: TaskType
    short_description: str = Field(min_length=1)
    importance: Importance = Importance.medium
    description: str | None = None
    prompt: str | None = None
    due_at: datetime | None = None
    parent_task_id: uuid.UUID | None = None
    assignee_employee_ids: list[uuid.UUID] = Field(default_factory=list)
    depends_on_task_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    requirement_id: uuid.UUID | None = None
    type: TaskType | None = None
    short_description: str | None = None
    description: str | None = None
    prompt: str | None = None
    importance: Importance | None = None
    status: TaskStatus | None = None
    due_at: datetime | None = None

class TaskOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    number: int
    parent_task_id: uuid.UUID | None
    requirement_id: uuid.UUID
    type: TaskType
    importance: Importance
    status: TaskStatus
    short_description: str
    description: str | None
    prompt: str | None
    due_at: datetime | None
    sort_order: int
    created_by: uuid.UUID | None
    created_at: datetime


class AssignmentCreate(BaseModel):
    employee_id: uuid.UUID


class TaskAssignmentOut(ORMModel):
    id: uuid.UUID
    task_id: uuid.UUID
    employee_id: uuid.UUID
    assigned_by: uuid.UUID | None
    assigned_at: datetime
    unassigned_at: datetime | None


class DependencyCreate(BaseModel):
    depends_on_task_id: uuid.UUID


class TaskAttachmentOut(ORMModel):
    id: uuid.UUID
    task_id: uuid.UUID
    storage_key: str
    filename: str | None
    mime_type: str | None
    size_bytes: int | None
    uploaded_by: uuid.UUID | None
    uploaded_at: datetime


class SubmitRequest(BaseModel):
    result_text: str | None = None


class ReviewRequest(BaseModel):
    accept: bool
    comment: str | None = None
