import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Importance, ReviewStatus, TaskStatus, TaskType
from app.db.base import Base, enum_col


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        sa.UniqueConstraint("project_id", "number", name="uq_task_project_number"),
        sa.Index("ix_tasks_project_status", "project_id", "status"),
        sa.Index("ix_tasks_requirement", "requirement_id"),
        sa.Index("ix_tasks_parent", "parent_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE")
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("requirements.id"), nullable=False
    )
    type: Mapped[TaskType] = mapped_column(enum_col(TaskType, "task_type"), nullable=False)
    importance: Mapped[Importance] = mapped_column(
        enum_col(Importance, "importance"),
        nullable=False,
        server_default=sa.text("'medium'"),
    )
    status: Mapped[TaskStatus] = mapped_column(
        enum_col(TaskStatus, "task_status"),
        nullable=False,
        server_default=sa.text("'open'"),
    )
    short_description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)
    prompt: Mapped[str | None] = mapped_column(sa.Text)
    due_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        sa.CheckConstraint("task_id <> depends_on_task_id", name="ck_task_dep_not_self"),
        sa.Index("ix_task_dependencies_depends_on", "depends_on_task_id"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        sa.Index("ix_task_assignments_task", "task_id"),
        sa.Index("ix_task_assignments_employee", "employee_id", "unassigned_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class TaskAttachment(Base):
    __tablename__ = "task_attachments"
    __table_args__ = (sa.Index("ix_task_attachments_task", "task_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    filename: Mapped[str | None] = mapped_column(sa.String(300))
    mime_type: Mapped[str | None] = mapped_column(sa.String(200))
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class TaskResultVersion(Base):
    __tablename__ = "task_result_versions"
    __table_args__ = (
        sa.UniqueConstraint("task_id", "version_no", name="uq_task_result_version"),
        sa.CheckConstraint(
            "review_status IS DISTINCT FROM 'rejected' OR "
            "(review_comment IS NOT NULL AND length(review_comment) > 0)",
            name="ck_task_result_rejected_comment",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    result_text: Mapped[str | None] = mapped_column(sa.Text)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    review_status: Mapped[ReviewStatus | None] = mapped_column(
        sa.Enum(
            ReviewStatus,
            name="review_status",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        )
    )
    review_comment: Mapped[str | None] = mapped_column(sa.Text)
