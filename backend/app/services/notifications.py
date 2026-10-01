"""In-app notifications."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


def notify(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    type_: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if user_id is None:
        return
    session.add(Notification(user_id=user_id, type=type_, payload=payload))
