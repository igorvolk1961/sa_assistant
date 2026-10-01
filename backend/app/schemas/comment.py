import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RoleCode


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    entity_type: str = Field(max_length=50)
    entity_id: uuid.UUID
    body: str = Field(min_length=1)


class CommentOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    author_user_id: uuid.UUID | None
    author_role_snapshot: RoleCode | None
    body: str
    created_at: datetime
    deleted_at: datetime | None
    deleted_by: uuid.UUID | None


class CommentAttachmentOut(ORMModel):
    id: uuid.UUID
    comment_id: uuid.UUID
    storage_key: str
    filename: str | None
    mime_type: str | None
    size_bytes: int | None
    uploaded_by: uuid.UUID | None
    uploaded_at: datetime


class NotificationOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    payload: dict | None
    is_read: bool
    created_at: datetime
