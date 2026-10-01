import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    CoverageStatus,
    JobStatus,
    MediaSource,
    MeetingFileKind,
    MeetingStatus,
    SegmentSource,
    TranscribeMode,
)
from app.db.base import Base, enum_col


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(sa.String(300))
    stakeholder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("stakeholders.id")
    )
    status: Mapped[MeetingStatus] = mapped_column(
        enum_col(MeetingStatus, "meeting_status"),
        nullable=False,
        server_default=sa.text("'planned'"),
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        sa.CheckConstraint(
            "num_nonnulls(user_id, employee_id, stakeholder_id) = 1",
            name="ck_meeting_participant_single_ref",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("employees.id")
    )
    stakeholder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("stakeholders.id")
    )
    meeting_role: Mapped[str | None] = mapped_column(sa.String(100))


class MeetingFile(Base):
    __tablename__ = "meeting_files"
    __table_args__ = (sa.Index("ix_meeting_files_meeting", "meeting_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[MeetingFileKind] = mapped_column(
        enum_col(MeetingFileKind, "meeting_file_kind"), nullable=False
    )
    source: Mapped[MediaSource] = mapped_column(
        enum_col(MediaSource, "media_source"),
        nullable=False,
        server_default=sa.text("'external'"),
    )
    storage_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    filename: Mapped[str | None] = mapped_column(sa.String(300))
    mime_type: Mapped[str | None] = mapped_column(sa.String(200))
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger)
    transcript_text: Mapped[str | None] = mapped_column(sa.Text)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class AudioRecording(Base):
    __tablename__ = "audio_recordings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[MediaSource] = mapped_column(
        enum_col(MediaSource, "media_source"),
        nullable=False,
        server_default=sa.text("'internal'"),
    )
    meeting_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meeting_files.id")
    )
    storage_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(sa.String(200))
    duration_sec: Mapped[int | None] = mapped_column(sa.Integer)
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger)
    checksum: Mapped[str | None] = mapped_column(sa.String(200))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


# TODO: not wired yet (M6/M7): transcription jobs are created once STT is enabled.
class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    recording_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("audio_recordings.id", ondelete="CASCADE")
    )
    stt_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("stt_models.id")
    )
    mode: Mapped[TranscribeMode] = mapped_column(
        enum_col(TranscribeMode, "transcribe_mode"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        enum_col(JobStatus, "job_status"),
        nullable=False,
        server_default=sa.text("'queued'"),
    )
    language: Mapped[str | None] = mapped_column(sa.String(20), server_default=sa.text("'ru-RU'"))
    session_limit_sec: Mapped[int | None] = mapped_column(sa.Integer)
    external_job_id: Mapped[str | None] = mapped_column(sa.String(200))
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(sa.Text)


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (sa.Index("ix_transcript_segments_meeting", "meeting_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    recording_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("audio_recordings.id")
    )
    start_ms: Mapped[int | None] = mapped_column(sa.Integer)
    end_ms: Mapped[int | None] = mapped_column(sa.Integer)
    speaker_label: Mapped[str | None] = mapped_column(sa.String(100))
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source: Mapped[SegmentSource] = mapped_column(
        enum_col(SegmentSource, "segment_source"),
        nullable=False,
        server_default=sa.text("'manual'"),
    )
    confidence: Mapped[Decimal | None] = mapped_column(sa.Numeric(4, 3))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class SegmentQuestionLink(Base):
    __tablename__ = "segment_question_links"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("transcript_segments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("mandatory_questions.id"), primary_key=True
    )


class MeetingQuestionCoverage(Base):
    __tablename__ = "meeting_question_coverage"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("mandatory_questions.id"), primary_key=True
    )
    status: Mapped[CoverageStatus] = mapped_column(
        sa.Enum(
            CoverageStatus,
            name="coverage_status",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        server_default=sa.text("'unanswered'"),
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("transcript_segments.id")
    )
