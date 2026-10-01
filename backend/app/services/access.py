"""Project visibility rules.

* open projects — visible to everyone (including guests);
* closed/archived — visible only to project admins (and the service owner).
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProjectStatus, RoleCode
from app.models import MembershipRole, Project, ProjectMembership, User


async def ensure_in_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    model,
    ref_id: uuid.UUID,
    name: str,
    *,
    status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT,
):
    obj = await session.get(model, ref_id)
    if obj is None or obj.project_id != project_id:
        raise HTTPException(
            status_code=status_code, detail=f"{name} does not belong to the project"
        )
    return obj


async def ensure_all_in_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    model,
    ref_ids: list[uuid.UUID],
    name: str,
) -> None:
    unique = set(ref_ids)
    if not unique:
        return
    found = set(
        (
            await session.execute(
                select(model.id).where(
                    model.id.in_(unique), model.project_id == project_id
                )
            )
        )
        .scalars()
        .all()
    )
    missing = unique - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{name} not in project: {sorted(str(m) for m in missing)}",
        )


def _admin_project_ids_subquery(user_id: uuid.UUID):
    return (
        select(MembershipRole.project_id)
        .join(ProjectMembership, ProjectMembership.id == MembershipRole.membership_id)
        .where(
            ProjectMembership.user_id == user_id,
            MembershipRole.role_code == RoleCode.admin,
        )
    )


async def list_visible_projects(session: AsyncSession, user: User) -> list[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    if not user.is_service_owner:
        stmt = stmt.where(
            or_(
                Project.status == ProjectStatus.open,
                Project.id.in_(_admin_project_ids_subquery(user.id)),
            )
        )
    return list((await session.execute(stmt)).scalars().all())
