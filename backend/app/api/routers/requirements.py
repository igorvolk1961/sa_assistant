"""Requirements (mandatory stakeholder link) and manual artifacts."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_role
from app.core.enums import RoleCode
from app.db.session import get_session
from app.models import (
    Artifact,
    Meeting,
    Position,
    Project,
    Requirement,
    Stakeholder,
    Task,
    User,
)
from app.schemas.requirement import (
    ArtifactCreate,
    ArtifactOut,
    ArtifactUpdate,
    RequirementCreate,
    RequirementOut,
    RequirementUpdate,
)
from app.schemas.task import TaskOut
from app.services.access import ensure_in_project

router = APIRouter(prefix="/projects/{project_id}", tags=["requirements"])

_VIEW = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee, RoleCode.guest)
_MANAGE = (RoleCode.admin, RoleCode.system_analyst)

_ARTIFACT_TYPES = {
    "view",
    "glossary",
    "use_case",
    "user_story",
    "constraint",
    "risk",
}


async def _stakeholder_or_422(
    session: AsyncSession, project_id: uuid.UUID, stakeholder_id: uuid.UUID
) -> Stakeholder:
    stakeholder = await session.get(Stakeholder, stakeholder_id)
    if stakeholder is None or stakeholder.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Stakeholder does not belong to the project",
        )
    return stakeholder


async def _position_or_422(session: AsyncSession, position_id: uuid.UUID) -> Position:
    position = await session.get(Position, position_id)
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Stakeholder type not found",
        )
    return position


async def _ensure_code_free(
    session: AsyncSession,
    project_id: uuid.UUID,
    code: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(Requirement).where(
        Requirement.project_id == project_id, Requirement.code == code
    )
    if exclude_id is not None:
        stmt = stmt.where(Requirement.id != exclude_id)
    if (await session.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirement with this code already exists in the project",
        )


async def _requirement_or_404(
    session: AsyncSession, project_id: uuid.UUID, requirement_id: uuid.UUID
) -> Requirement:
    requirement = await session.get(Requirement, requirement_id)
    if requirement is None or requirement.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found"
        )
    return requirement


@router.get("/requirements", response_model=list[RequirementOut])
async def list_requirements(
    stakeholder_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Requirement]:
    project, _, _ = ctx
    stmt = select(Requirement).where(Requirement.project_id == project.id)
    if stakeholder_id is not None:
        stmt = stmt.where(Requirement.stakeholder_id == stakeholder_id)
    return list(
        (
            await session.execute(
                stmt.order_by(Requirement.created_at).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post("/requirements", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Requirement:
    project, actor, _ = ctx
    data = payload.model_dump()
    if data.get("stakeholder_id") is not None:
        await _stakeholder_or_422(session, project.id, data["stakeholder_id"])
    if data.get("stakeholder_type_id") is not None:
        await _position_or_422(session, data["stakeholder_type_id"])
    if data.get("code") is not None:
        await _ensure_code_free(session, project.id, data["code"])
    requirement = Requirement(project_id=project.id, created_by=actor.id, **data)
    session.add(requirement)
    await session.commit()
    await session.refresh(requirement)
    return requirement


@router.get("/requirements/{requirement_id}", response_model=RequirementOut)
async def get_requirement(
    requirement_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> Requirement:
    project, _, _ = ctx
    return await _requirement_or_404(session, project.id, requirement_id)


@router.patch("/requirements/{requirement_id}", response_model=RequirementOut)
async def update_requirement(
    requirement_id: uuid.UUID,
    payload: RequirementUpdate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Requirement:
    project, _, _ = ctx
    requirement = await _requirement_or_404(session, project.id, requirement_id)
    data = payload.model_dump(exclude_unset=True)
    if "stakeholder_id" in data and data["stakeholder_id"] is not None:
        await _stakeholder_or_422(session, project.id, data["stakeholder_id"])
    if "stakeholder_type_id" in data and data["stakeholder_type_id"] is not None:
        await _position_or_422(session, data["stakeholder_type_id"])
    if "code" in data and data["code"] is not None:
        await _ensure_code_free(session, project.id, data["code"], exclude_id=requirement.id)
    for field, value in data.items():
        setattr(requirement, field, value)
    await session.commit()
    await session.refresh(requirement)
    return requirement


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    requirement = await _requirement_or_404(session, project.id, requirement_id)
    has_tasks = (
        await session.execute(select(Task.id).where(Task.requirement_id == requirement.id).limit(1))
    ).scalar_one_or_none()
    if has_tasks is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requirement has linked tasks; delete or reassign them first",
        )
    await session.delete(requirement)
    await session.commit()


@router.get("/requirements/{requirement_id}/tasks", response_model=list[TaskOut])
async def tasks_of_requirement(
    requirement_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Task]:
    project, _, _ = ctx
    await _requirement_or_404(session, project.id, requirement_id)
    return list(
        (
            await session.execute(
                select(Task)
                .where(Task.requirement_id == requirement_id)
                .order_by(Task.number)
            )
        )
        .scalars()
        .all()
    )


# ----------------------------- Manual artifacts -----------------------------
@router.get("/artifacts", response_model=list[ArtifactOut])
async def list_artifacts(
    type: str | None = None,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Artifact]:
    project, _, _ = ctx
    stmt = select(Artifact).where(Artifact.project_id == project.id)
    if type is not None:
        stmt = stmt.where(Artifact.type == type)
    return list((await session.execute(stmt.order_by(Artifact.created_at))).scalars().all())


@router.post("/artifacts", response_model=ArtifactOut, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    payload: ArtifactCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Artifact:
    project, actor, _ = ctx
    if payload.type not in _ARTIFACT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"type must be one of {sorted(_ARTIFACT_TYPES)}",
        )
    if payload.meeting_id is not None:
        await ensure_in_project(session, project.id, Meeting, payload.meeting_id, "Meeting")
    artifact = Artifact(
        project_id=project.id,
        meeting_id=payload.meeting_id,
        type=payload.type,
        content=payload.content,
        source=payload.source,
        created_by=actor.id,
    )
    session.add(artifact)
    await session.commit()
    await session.refresh(artifact)
    return artifact


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactOut)
async def update_artifact(
    artifact_id: uuid.UUID,
    payload: ArtifactUpdate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Artifact:
    project, _, _ = ctx
    artifact = await session.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    if payload.content is not None:
        artifact.content = payload.content
        artifact.version += 1
    await session.commit()
    await session.refresh(artifact)
    return artifact


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    artifact = await session.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    await session.delete(artifact)
    await session.commit()
