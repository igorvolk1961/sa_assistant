import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    DiagramType,
    ImplementationStatus,
    Importance,
    JobStatus,
    PriorityMoscow,
    RequirementType,
)
from app.db.base import Base, enum_col


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        sa.Index("ix_requirements_stakeholder", "stakeholder_id"),
        sa.Index("ix_requirements_project", "project_id"),
        sa.Index(
            "uq_requirement_project_code",
            "project_id",
            "code",
            unique=True,
            postgresql_where=sa.text("code IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    stakeholder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("stakeholders.id")
    )
    stakeholder_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("positions.id")
    )
    code: Mapped[str | None] = mapped_column(sa.String(50))
    epic: Mapped[str | None] = mapped_column(sa.String(300))
    type: Mapped[RequirementType] = mapped_column(
        enum_col(RequirementType, "requirement_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(300), nullable=False)
    short_description: Mapped[str | None] = mapped_column(sa.Text)
    description: Mapped[str | None] = mapped_column(sa.Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(sa.Text)
    nfr_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("nfr_types.id")
    )
    importance: Mapped[Importance] = mapped_column(
        enum_col(Importance, "importance"),
        nullable=False,
        server_default=sa.text("'medium'"),
    )
    priority_moscow: Mapped[PriorityMoscow | None] = mapped_column(
        enum_col(PriorityMoscow, "priority_moscow")
    )
    implementation_status: Mapped[ImplementationStatus | None] = mapped_column(
        enum_col(ImplementationStatus, "implementation_status")
    )
    status: Mapped[str | None] = mapped_column(sa.String(50), server_default=sa.text("'draft'"))
    source: Mapped[str | None] = mapped_column(sa.String(100))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        sa.CheckConstraint(
            "type IN ('view','glossary','use_case','user_story','constraint','risk')",
            name="ck_artifact_type",
        ),
        sa.CheckConstraint("source IN ('auto','manual')", name="ck_artifact_source"),
        sa.Index("ix_artifacts_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id")
    )
    type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default=sa.text("'auto'")
    )
    version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("1")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


# TODO: not wired yet (M8): analysis runs are created once LLM analysis is enabled.
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("meetings.id")
    )
    llm_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("llm_models.id")
    )
    kind: Mapped[str | None] = mapped_column(sa.String(100))
    status: Mapped[JobStatus] = mapped_column(
        enum_col(JobStatus, "job_status"),
        nullable=False,
        server_default=sa.text("'queued'"),
    )
    prompt: Mapped[str | None] = mapped_column(sa.Text)
    response: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


# TODO: not wired yet (M11): C4/BPMN diagram generation.
class Diagram(Base):
    __tablename__ = "diagrams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[DiagramType] = mapped_column(
        enum_col(DiagramType, "diagram_type"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(sa.String(300))
    format: Mapped[str | None] = mapped_column(sa.String(50), server_default=sa.text("'dsl'"))
    content: Mapped[str | None] = mapped_column(sa.Text)
    version: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("1"))
    generated_by_llm: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("true")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
