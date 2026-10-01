import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import RoleCode
from app.db.base import Base, enum_col


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    login: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    last_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(sa.String(100))
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    # Платформенный владелец сервиса: глобальные справочники и панель ресурсов.
    is_service_owner: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[RoleCode] = mapped_column(enum_col(RoleCode, "role_code"), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
