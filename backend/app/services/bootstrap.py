"""Startup bootstrap: default roles and the service owner account.

The stakeholder-type / position catalogue is filled from the stakeholder
registry document via ``scripts/import_stakeholder_types.py`` (not seeded here).
"""

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import RoleCode
from app.core.security import hash_password, verify_password
from app.db.session import SessionFactory
from app.models import Role, User

logger = logging.getLogger(__name__)

DEFAULT_ROLES: dict[RoleCode, str] = {
    RoleCode.admin: "Администратор",
    RoleCode.system_analyst: "Системный аналитик",
    RoleCode.employee: "Сотрудник",
    RoleCode.guest: "Гость",
}


async def bootstrap() -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        for code, name in DEFAULT_ROLES.items():
            if await session.get(Role, code) is None:
                session.add(Role(code=code, name=name))

        owner = (
            await session.execute(
                select(User).where(User.login == settings.bootstrap_owner_login)
            )
        ).scalar_one_or_none()
        if owner is None:
            session.add(
                User(
                    login=settings.bootstrap_owner_login,
                    password_hash=hash_password(settings.bootstrap_owner_password),
                    last_name="Владелец",
                    first_name="Сервиса",
                    is_service_owner=True,
                )
            )
            logger.info("Created service owner '%s'", settings.bootstrap_owner_login)
            if settings.app_env != "production":
                logger.warning(
                    "DEV bootstrap owner '%s' password: %s",
                    settings.bootstrap_owner_login,
                    settings.bootstrap_owner_password,
                )
        else:
            if not owner.is_service_owner:
                owner.is_service_owner = True
            # In production the owner password must be set explicitly, so we never
            # rotate it here; in dev keep it in sync with the (random) config value.
            if settings.app_env != "production" and not verify_password(
                settings.bootstrap_owner_password, owner.password_hash
            ):
                owner.password_hash = hash_password(settings.bootstrap_owner_password)

        await session.commit()
