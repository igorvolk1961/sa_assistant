import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.enums import ProjectStatus, RoleCode
from app.core.security import decode_token
from app.db.session import get_session
from app.models import MembershipRole, Project, ProjectMembership, User

bearer_scheme = HTTPBearer(auto_error=False)

_ROLE_PRIORITY = {
    RoleCode.admin: 3,
    RoleCode.system_analyst: 2,
    RoleCode.employee: 1,
    RoleCode.guest: 0,
}


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_token(credentials.credentials, settings)
    except Exception as exc:  # noqa: BLE001
        raise _unauthorized("Invalid token") from exc
    if payload.get("type") != "access":
        raise _unauthorized("Invalid token type")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized("Invalid token subject") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


async def require_service_owner(user: User = Depends(get_current_user)) -> User:
    if not user.is_service_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Service owner only")
    return user


async def get_project_role(
    session: AsyncSession, user: User, project_id: uuid.UUID
) -> tuple[Project, RoleCode | None]:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if user.is_service_owner:
        return project, RoleCode.admin
    membership = (
        await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        return project, None
    role_codes = (
        await session.execute(
            select(MembershipRole.role_code).where(
                MembershipRole.membership_id == membership.id
            )
        )
    ).scalars().all()
    if not role_codes:
        return project, None
    return project, max(role_codes, key=lambda r: _ROLE_PRIORITY[r])


def require_project_role(*allowed: RoleCode):
    """Dependency factory. Reads ``project_id`` from the path."""

    async def dependency(
        project_id: uuid.UUID,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> tuple[Project, User, RoleCode]:
        project, role = await get_project_role(session, user, project_id)
        effective = role if role is not None else RoleCode.guest
        if project.status != ProjectStatus.open and effective != RoleCode.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Closed/archived projects are admin-only",
            )
        if effective not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in allowed)}",
            )
        return project, user, effective

    return dependency
