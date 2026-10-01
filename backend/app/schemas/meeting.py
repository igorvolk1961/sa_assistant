import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    CoverageStatus,
    MediaSource,
    MeetingFileKind,
    MeetingStatus,
    SegmentSource,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MeetingCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    stakeholder_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    participant_employee_ids: list[uuid.UUID] = Field(default_factory=list)
    participant_stakeholder_ids: list[uuid.UUID] = Field(default_factory=list)


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    stakeholder_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    status: MeetingStatus | None = None


class MeetingOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str | None
    stakeholder_id: uuid.UUID | None
    status: MeetingStatus
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    created_by: uuid.UUID | None


class MeetingFileOut(ORMModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    kind: MeetingFileKind
    source: MediaSource
    storage_key: str
    filename: str | None
    mime_type: str | None
    size_bytes: int | None
    transcript_text: str | None
    uploaded_by: uuid.UUID | None
    uploaded_at: datetime


class SegmentCreate(BaseModel):
    text: str = Field(min_length=1)
    speaker_label: str | None = Field(default=None, max_length=100)
    start_ms: int | None = None
    end_ms: int | None = None


class SegmentUpdate(BaseModel):
    text: str | None = None
    speaker_label: str | None = Field(default=None, max_length=100)
    start_ms: int | None = None
    end_ms: int | None = None


class SegmentOut(ORMModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    start_ms: int | None
    end_ms: int | None
    speaker_label: str | None
    text: str
    source: SegmentSource
    created_by: uuid.UUID | None
    updated_at: datetime | None
    created_at: datetime


class SegmentQuestionLinkCreate(BaseModel):
    question_id: uuid.UUID


class CoverageOut(ORMModel):
    meeting_id: uuid.UUID
    question_id: uuid.UUID
    status: CoverageStatus
    segment_id: uuid.UUID | None


class UnansweredQuestionOut(BaseModel):
    question_id: uuid.UUID
    text: str
    position_id: uuid.UUID
    status: CoverageStatus
