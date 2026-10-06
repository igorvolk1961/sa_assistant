"""Replace the stakeholder-type catalogue from a stakeholder registry document.

- Parses the markdown registry into stakeholder types (``positions``).
- Deletes old types and inserts the new ones.
- Re-links requirements of a project to the new types by re-reading the FR/NFR
  documents (NFR «Заказчик», FR «Стейкхолдер:»).

Usage:
    uv run python scripts/import_stakeholder_types.py \
        --stakeholders <02_stakeholders.md> --project-name TenderSearch \
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

from sqlalchemy import select, update  # noqa: E402

from app.db.session import SessionFactory  # noqa: E402
from app.models import Position, Project, Requirement, Stakeholder  # noqa: E402

FR_ID = re.compile(r"^FR-\d+\.\d+$")
NFR_ID = re.compile(r"^NFR-[A-Z]+-\d+$")

# Priority order matters: more specific roles first.
PRIORITY = [
    "конечный клиент",
    "заказчик",
    "product owner",
    "предметный эксперт",
    "системный администратор",
    "сист.администратор",
    "devops",
    "security",
    "release",
    "qa",
    "юрист",
    "разработчик",
    "аналитик",
    "тендеролог",
]
# key -> substring that must be present in the type name
KEY_TARGET = {
    "конечный клиент": "конечный клиент",
    "заказчик": "конечный клиент",
    "product owner": "product owner",
    "предметный эксперт": "предметный эксперт",
    "системный администратор": "системный администратор",
    "сист.администратор": "системный администратор",
    "devops": "devops",
    "security": "security",
    "release": "release",
    "qa": "qa",
    "юрист": "юрист",
    "разработчик": "разработчик",
    "аналитик": "предметный эксперт",
    "тендеролог": "тендеролог",
}


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_types(path: pathlib.Path) -> list[dict]:
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        parts = cells(line)
        if len(parts) < 5:
            continue
        role = parts[0]
        if not role or role.lower().startswith("роль") or set(role) <= set(":- "):
            continue
        out.append(
            {
                "name": role,
                "representatives": parts[1] or None,
                "category": parts[2] or None,
                "description": parts[3] or None,
                "influence": parts[4] or None,
            }
        )
    return out


def user_function(text: str) -> str:
    """Extract the stakeholder mention from an FR text."""
    low = text.lower()
    for marker in ("стейкхолдер:", "стейкхолдеры:", "заказчик:"):
        idx = low.find(marker)
        if idx != -1:
            return text[idx + len(marker) :]
    return ""


def match_type(text: str, types: list[Position]) -> uuid.UUID | None:
    if not text:
        return None
    low = text.lower()
    for key in PRIORITY:
        if key in low:
            target = KEY_TARGET[key]
            for position in types:
                if target in position.name.lower():
                    return position.id
    return None


def parse_fr_texts(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        parts = cells(line)
        if len(parts) < 2 or not FR_ID.match(parts[0]):
            continue
        result[parts[0]] = parts[1]
    return result


def parse_nfr_customers(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    customer = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("**Заказчик**") and ":" in line:
            customer = line.split(":", 1)[1].strip().strip("*")
            continue
        if not line.startswith("|"):
            continue
        parts = cells(line)
        if len(parts) >= 3 and NFR_ID.match(parts[0]):
            result[parts[0]] = customer
    return result


async def resolve_project(session, name: str) -> Project:
    project = (
        await session.execute(select(Project).where(Project.name == name))
    ).scalar_one_or_none()
    if project is None:
        raise SystemExit(f"Project '{name}' not found")
    return project


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stakeholders", type=pathlib.Path, required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--fr", type=pathlib.Path)
    parser.add_argument("--nfr", type=pathlib.Path)
    args = parser.parse_args()

    type_data = parse_types(args.stakeholders)
    if not type_data:
        raise SystemExit("No stakeholder types parsed")

    async with SessionFactory() as session:
        old_positions = list((await session.execute(select(Position))).scalars().all())
        old_names = {p.id: p.name for p in old_positions}

        # Detach requirement links first.
        await session.execute(update(Requirement).values(stakeholder_type_id=None))

        stakeholders = list((await session.execute(select(Stakeholder))).scalars().all())
        old_project = await resolve_project(session, args.project_name)

        new_positions: list[Position] = []
        for index, data in enumerate(type_data):
            position = Position(
                code="role_" + hashlib.md5(data["name"].encode("utf-8")).hexdigest()[:8],  # noqa: S324
                name=data["name"],
                description=data["description"],
                category=data["category"],
                representatives=data["representatives"],
                influence=data["influence"],
                sort_order=index,
            )
            session.add(position)
            new_positions.append(position)
        await session.flush()

        # Move existing stakeholders to the closest new type, then delete old types.
        for stakeholder in stakeholders:
            matched = match_type(old_names.get(stakeholder.position_id, ""), new_positions)
            stakeholder.position_id = matched or new_positions[0].id
        await session.flush()
        for position in old_positions:
            await session.delete(position)
        await session.flush()

        # Re-link requirements.
        fr_texts = parse_fr_texts(args.fr) if args.fr else {}
        nfr_customers = parse_nfr_customers(args.nfr) if args.nfr else {}
        requirements = list(
            (
                await session.execute(
                    select(Requirement).where(Requirement.project_id == old_project.id)
                )
            )
            .scalars()
            .all()
        )
        linked = 0
        for requirement in requirements:
            if requirement.code is None:
                continue
            if NFR_ID.match(requirement.code):
                text = nfr_customers.get(requirement.code, "")
            else:
                text = user_function(fr_texts.get(requirement.code, ""))
            matched = match_type(text, new_positions)
            if matched is not None:
                requirement.stakeholder_type_id = matched
                linked += 1

        await session.commit()
        print(f"Stakeholder types: {len(old_positions)} old -> {len(new_positions)} new")
        print(f"Requirements re-linked: {linked}")


if __name__ == "__main__":
    asyncio.run(main())
