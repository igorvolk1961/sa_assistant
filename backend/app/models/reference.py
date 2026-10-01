import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Position(Base):
    """Должность = тип стейкхолдера (глобальный справочник)."""

    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    assignable_as_position: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    usable_as_stakeholder_type: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    is_system: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )


class MandatoryQuestion(Base):
    __tablename__ = "mandatory_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("positions.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )


class NfrType(Base):
    __tablename__ = "nfr_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    code: Mapped[str | None] = mapped_column(sa.String(100), unique=True)
    name: Mapped[str | None] = mapped_column(sa.String(200))
    description: Mapped[str | None] = mapped_column(sa.Text)


class LlmModel(Base):
    __tablename__ = "llm_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    provider: Mapped[str | None] = mapped_column(sa.String(100))
    model_code: Mapped[str | None] = mapped_column(sa.String(200))
    display_name: Mapped[str | None] = mapped_column(sa.String(200))
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    params: Mapped[dict | None] = mapped_column(JSONB)


class SttModel(Base):
    __tablename__ = "stt_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    provider: Mapped[str | None] = mapped_column(sa.String(100))
    model_code: Mapped[str | None] = mapped_column(sa.String(200))
    display_name: Mapped[str | None] = mapped_column(sa.String(200))
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    supports_streaming: Mapped[bool | None] = mapped_column(sa.Boolean)
    supports_diarization: Mapped[bool | None] = mapped_column(sa.Boolean)
    session_limit_sec: Mapped[int | None] = mapped_column(sa.Integer)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    purpose: Mapped[str | None] = mapped_column(sa.String(100))
    name: Mapped[str | None] = mapped_column(sa.String(200))
    template: Mapped[str | None] = mapped_column(sa.Text)
    is_system: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )


# TODO: not wired yet (M6/M7): provider secrets for STT/LLM.
class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    provider: Mapped[str | None] = mapped_column(sa.String(100))
    scope: Mapped[str | None] = mapped_column(sa.String(100))
    encrypted_secret: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
