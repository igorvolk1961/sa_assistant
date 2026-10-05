"""Startup bootstrap: default roles, reference positions, and the service owner account."""

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import RoleCode
from app.core.security import hash_password, verify_password
from app.db.session import SessionFactory
from app.models import Position, Role, User

logger = logging.getLogger(__name__)

DEFAULT_ROLES: dict[RoleCode, str] = {
    RoleCode.admin: "Администратор",
    RoleCode.system_analyst: "Системный аналитик",
    RoleCode.employee: "Сотрудник",
    RoleCode.guest: "Гость",
}

# Position = тип стейкхолдера / должность (глобальный справочник).
# Должности, пригодные как тип стейкхолдера:
POSITION_STAKEHOLDER_TYPES: tuple[tuple[str, str], ...] = (
    ("customer", "Заказчик"),
    ("user", "Пользователь"),
    ("executive", "Руководитель"),
    ("expert", "Эксперт"),
    ("regulator", "Регулирующий орган"),
    ("partner", "Партнёр"),
)

# Должности-роли, которые можно назначать сотрудникам как должность:
POSITION_ASSIGNABLE: tuple[tuple[str, str], ...] = (
    ("system_analyst", "Системный аналитик"),
    ("developer", "Разработчик"),
    ("tester", "Тестировщик"),
    ("designer", "Дизайнер"),
    ("ba", "Бизнес-аналитик"),
)

DEFAULT_POSITIONS: tuple[tuple[str, str, bool, bool], ...] = (
    # (code, name, assignable_as_position, usable_as_stakeholder_type)
    *((code, name, False, True) for code, name in POSITION_STAKEHOLDER_TYPES),
    *((code, name, True, False) for code, name in POSITION_ASSIGNABLE),
)


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

        for code, name, assignable, usable_as_type in DEFAULT_POSITIONS:
            position = (
                await session.execute(select(Position).where(Position.code == code))
            ).scalar_one_or_none()
            if position is None:
                session.add(
                    Position(
                        code=code,
                        name=name,
                        assignable_as_position=assignable,
                        usable_as_stakeholder_type=usable_as_type,
                    )
                )
                logger.info("Created position '%s' (%s)", code, name)
            else:
                if position.name != name:
                    position.name = name
                if position.assignable_as_position != assignable:
                    position.assignable_as_position = assignable
                if position.usable_as_stakeholder_type != usable_as_type:
                    position.usable_as_stakeholder_type = usable_as_type

        await session.commit()
