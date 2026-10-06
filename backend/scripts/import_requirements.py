"""Import functional/non-functional requirements from markdown into a project.

Parses the table-based FR/NFR documents and upserts requirements by code.

Usage:
    uv run python scripts/import_requirements.py --project-name TenderSearch \
        --fr <functional_requirements.md> --nfr <non_functional_requirements.md>
"""

import argparse
import asyncio
import hashlib
import pathlib
import re
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.enums import (  # noqa: E402
    ImplementationStatus,
    PriorityMoscow,
    RequirementType,
)
from app.db.session import SessionFactory  # noqa: E402
from app.models import NfrType, Position, Project, Requirement  # noqa: E402

FR_ID = re.compile(r"^FR-\d+\.\d+$")
NFR_ID = re.compile(r"^NFR-[A-Z]+-\d+$")

PRIORITY = {
    "must": PriorityMoscow.must,
    "should": PriorityMoscow.should,
    "could": PriorityMoscow.could,
}

NFR_TYPES = {
    "COST": "Стоимость",
    "PERF": "Производительность",
    "SEC": "Безопасность",
    "REL": "Надёжность",
    "OBS": "Наблюдаемость",
    "FT": "Отказоустойчивость",
}


def short(text: str, limit: int = 120) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def map_priority(value: str) -> PriorityMoscow | None:
    return PRIORITY.get(value.strip().lower())


def map_status(value: str) -> ImplementationStatus:
    if "🟡" in value:
        return ImplementationStatus.partial
    if "❌" in value:
        return ImplementationStatus.missing
    if "✅" in value:
        return ImplementationStatus.implemented
    return ImplementationStatus.unknown


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_fr(path: pathlib.Path) -> list[dict]:
    rows: list[dict] = []
    epic = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            epic = line[3:].strip()
            continue
        if not line.startswith("|"):
            continue
        parts = cells(line)
        if len(parts) < 5 or not FR_ID.match(parts[0]):
            continue
        text = parts[1]
        rows.append(
            {
                "code": parts[0],
                "epic": epic,
                "text": text,
                "priority": map_priority(parts[2]),
                "status": map_status(parts[4]),
            }
        )
    return rows


def parse_nfr(path: pathlib.Path) -> list[dict]:
    rows: list[dict] = []
    epic = None
    customer = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            epic = line[3:].strip()
            continue
        if line.startswith("**Заказчик**"):
            customer = line.split(":", 1)[1].strip().strip("*") if ":" in line else None
            continue
        if not line.startswith("|"):
            continue
        parts = cells(line)
        if len(parts) < 3 or not NFR_ID.match(parts[0]):
            continue
        rows.append(
            {
                "code": parts[0],
                "epic": epic,
                "name": parts[1],
                "metric": parts[2],
                "customer": customer,
            }
        )
    return rows


def nfr_code(code: str) -> str:
    return code.split("-")[1]


def position_code(name: str) -> str:
    return "stk_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8]  # noqa: S324


async def resolve_project(session, project_id: uuid.UUID | None, name: str | None) -> Project:
    if project_id is not None:
        project = await session.get(Project, project_id)
        if project is None:
            raise SystemExit(f"Project {project_id} not found")
        return project
    project = (
        await session.execute(select(Project).where(Project.name == name))
    ).scalar_one_or_none()
    if project is None:
        project = Project(name=name)
        session.add(project)
        await session.flush()
    return project


async def ensure_nfr_type(session, code: str) -> uuid.UUID:
    nfr_type = (
        await session.execute(select(NfrType).where(NfrType.code == code))
    ).scalar_one_or_none()
    if nfr_type is None:
        nfr_type = NfrType(code=code, name=NFR_TYPES.get(code, code))
        session.add(nfr_type)
        await session.flush()
    return nfr_type.id


async def ensure_position(session, customer: str) -> uuid.UUID | None:
    name = customer.split(",")[0].split("/")[0].strip()
    if not name:
        return None
    position = (
        await session.execute(select(Position).where(Position.name == name))
    ).scalar_one_or_none()
    if position is None:
        position = Position(code=position_code(name), name=name)
        session.add(position)
        await session.flush()
    return position.id


async def upsert(session, project_id: uuid.UUID, values: dict) -> str:
    existing = (
        await session.execute(
            select(Requirement).where(
                Requirement.project_id == project_id, Requirement.code == values["code"]
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(Requirement(project_id=project_id, **values))
        return "added"
    for field, value in values.items():
        setattr(existing, field, value)
    return "updated"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", type=uuid.UUID)
    parser.add_argument("--project-name")
    parser.add_argument("--fr", type=pathlib.Path)
    parser.add_argument("--nfr", type=pathlib.Path)
    args = parser.parse_args()
    if not args.project_id and not args.project_name:
        raise SystemExit("Provide --project-id or --project-name")
    if not args.fr and not args.nfr:
        raise SystemExit("Provide --fr and/or --nfr")

    async with SessionFactory() as session:
        project = await resolve_project(session, args.project_id, args.project_name)
        counted = {"added": 0, "updated": 0}

        if args.fr:
            for row in parse_fr(args.fr):
                values = {
                    "code": row["code"],
                    "epic": row["epic"],
                    "type": RequirementType.functional,
                    "title": short(row["text"]),
                    "short_description": short(row["text"]),
                    "description": row["text"],
                    "priority_moscow": row["priority"],
                    "implementation_status": row["status"],
                }
                counted[await upsert(session, project.id, values)] += 1

        if args.nfr:
            for row in parse_nfr(args.nfr):
                code = nfr_code(row["code"])
                nfr_type_id = await ensure_nfr_type(session, code)
                stakeholder_type_id = (
                    await ensure_position(session, row["customer"]) if row["customer"] else None
                )
                values = {
                    "code": row["code"],
                    "epic": row["epic"],
                    "type": RequirementType.nonfunctional,
                    "title": short(row["name"]),
                    "short_description": row["name"],
                    "description": row["metric"],
                    "acceptance_criteria": row["metric"],
                    "nfr_type_id": nfr_type_id,
                    "stakeholder_type_id": stakeholder_type_id,
                    "implementation_status": ImplementationStatus.unknown,
                }
                counted[await upsert(session, project.id, values)] += 1

        await session.commit()
        print(f"Project: {project.name} ({project.id})")
        print(f"Requirements added: {counted['added']}, updated: {counted['updated']}")


if __name__ == "__main__":
    asyncio.run(main())
