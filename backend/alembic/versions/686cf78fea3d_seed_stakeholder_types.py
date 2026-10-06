"""seed stakeholder types

Pre-populates the stakeholder-type catalogue (``positions``) with the roles from
the stakeholder registry. This is the only reference-data seed kept in migrations.

Revision ID: 686cf78fea3d
Revises: e94efb165f4c
Create Date: 2026-10-06 18:20:00.000000

"""
import hashlib
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '686cf78fea3d'
down_revision: str | None = 'e94efb165f4c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (name, description, category, representatives, influence)
STAKEHOLDER_TYPES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "Product Owner (Владелец продукта)",
        "Экономика проекта, запуск коммерческого SaaS-продукта, контроль ROI, "
        "определение приоритетов",
        "Внутренний",
        "Дмитрий",
        "Высокое",
    ),
    (
        "Предметный эксперт (SME) / Эксперт по закупкам",
        "Точная интерпретация юридических и регуляторных требований в ТЗ "
        "(ПП 2571, реестр Минпромторга, лицензии), минимизация рисков участия в "
        "непроходных тендерах",
        "Внешний",
        "Александр",
        "Критическое (для бизнес-логики)",
    ),
    (
        "Тендеролог (Пользователь системы)",
        "Сокращение рутины (с 1.5 ч до 15 мин), удобный интерфейс, оперативные "
        "уведомления, гарантия изоляции своих данных и профилей от других пользователей",
        "Внешний",
        "Александр (как пример пользователя), будущие пользователи",
        "Высокое",
    ),
    (
        "Конечный клиент тендеролога",
        "Получение от тендеролога проверенной, юридически безопасной сводки "
        "подходящих закупок",
        "Внешний",
        "Дмитрий (как пример клиента)",
        "Среднее",
    ),
    (
        "Разработчик / Проектировщик",
        "Реализация функционала, выбор архитектурных паттернов, поддержка кода, "
        "возможное партнерство",
        "Внутренний",
        "Игорь",
        "Высокое",
    ),
    (
        "DevOps / Инженер по надежности (SRE)",
        "Отказоустойчивость, масштабируемость, наблюдаемость (мониторинг, логи), "
        "контроль затрат на инфраструктуру (cost per record)",
        "Внутренний",
        "частично Игорь, ищем выделенного",
        "Высокое",
    ),
    (
        "Системный администратор",
        "Управление учетными записями, контроль изоляции данных (мультитенантность), "
        "мониторинг активности",
        "Внутренний",
        "Игорь (фактически, как admin/разработчик); выделенный не назначен",
        "Среднее",
    ),
    (
        "QA / Инженер по тестированию",
        "Проверяемость требований, регресс-защита (регресс-гейт скоринга), "
        "приёмочные критерии (Acceptance Criteria), связь тестов с требованиями",
        "Внутренний",
        "пока не назначен",
        "Среднее",
    ),
    (
        "Security / DPO (защита данных)",
        "Соблюдение 152-ФЗ (ПДн в текстах ТЗ), легальность и риски парсинга "
        "(robots.txt, официальные API), маскирование/нехранение персональных данных, "
        "юридический дисклеймер",
        "Внутренний",
        "пока не назначен",
        "Высокое (может заблокировать релиз)",
    ),
    (
        "Release / Maintenance",
        "Планирование релизов, миграции БД (Liquibase), обратная совместимость, "
        "управление конфигурациями и их промоцией, откатные планы",
        "Внутренний",
        "пока не назначен",
        "Среднее",
    ),
    (
        "Юрист компании / Compliance-офицер",
        "Обеспечение легальности методов сбора данных (парсинг), соблюдение 152-ФЗ "
        "(если в тендерах есть персональные данные), минимизация рисков претензий "
        "из-за некорректной автоматической интерпретации условий ТЗ, проверка "
        "пользовательских соглашений (для SaaS)",
        "Внутренний",
        "пока не назначен",
        "Высокое (может заблокировать релиз или определенные фичи)",
    ),
)


def _code(name: str) -> str:
    return "role_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8]  # noqa: S324


def upgrade() -> None:
    conn = op.get_bind()
    for index, (name, description, category, representatives, influence) in enumerate(
        STAKEHOLDER_TYPES
    ):
        conn.execute(
            sa.text(
                "INSERT INTO positions "
                "(code, name, description, category, representatives, influence, "
                " sort_order, assignable_as_position, usable_as_stakeholder_type, is_system) "
                "VALUES (:code, :name, :description, :category, :representatives, "
                " :influence, :sort_order, true, true, false) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {
                "code": _code(name),
                "name": name,
                "description": description,
                "category": category,
                "representatives": representatives,
                "influence": influence,
                "sort_order": index,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    for name, *_ in STAKEHOLDER_TYPES:
        conn.execute(
            sa.text("DELETE FROM positions WHERE code = :code"), {"code": _code(name)}
        )
