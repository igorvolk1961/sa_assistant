import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_project_role, require_project_role
from app.core.enums import ProjectStatus, RoleCode
from app.db.session import get_session
from app.models import (
    Artifact,
    AuditLog,
    Comment,
    Diagram,
    Employee,
    Meeting,
    MembershipRole,
    Project,
    ProjectMembership,
    Requirement,
    RequirementEpic,
    Stakeholder,
    Task,
    User,
)
from app.schemas.project import (
    MemberAdd,
    MemberOut,
    MemberRolesUpdate,
    ProjectCreate,
    ProjectOut,
    TransferAnalystRequest,
)
from app.services.access import list_visible_projects
from app.services.audit import record

router = APIRouter(prefix="/projects", tags=["projects"])

_VALID_ROLE_SETS = {frozenset({RoleCode.admin, RoleCode.system_analyst})}


def _validate_roles(roles: list[RoleCode]) -> list[RoleCode]:
    unique = list(dict.fromkeys(roles))
    if not unique:
        raise HTTPException(status_code=422, detail="At least one role is required")
    if len(unique) > 2 or (len(unique) == 2 and frozenset(unique) not in _VALID_ROLE_SETS):
        raise HTTPException(
            status_code=422,
            detail="Only one role is allowed, except the pair {admin, system_analyst}",
        )
    return unique


async def _roles_of(session: AsyncSession, membership_id: uuid.UUID) -> list[RoleCode]:
    return list(
        (
            await session.execute(
                select(MembershipRole.role_code).where(
                    MembershipRole.membership_id == membership_id
                )
            )
        )
        .scalars()
        .all()
    )


async def _replace_roles(
    session: AsyncSession, membership: ProjectMembership, roles: list[RoleCode]
) -> None:
    await session.execute(
        delete(MembershipRole).where(MembershipRole.membership_id == membership.id)
    )
    for role in roles:
        session.add(
            MembershipRole(
                membership_id=membership.id, role_code=role, project_id=membership.project_id
            )
        )


async def _find_analyst_membership(
    session: AsyncSession, project_id: uuid.UUID
) -> ProjectMembership | None:
    return (
        await session.execute(
            select(ProjectMembership)
            .join(MembershipRole, MembershipRole.membership_id == ProjectMembership.id)
            .where(
                ProjectMembership.project_id == project_id,
                MembershipRole.role_code == RoleCode.system_analyst,
            )
        )
    ).scalar_one_or_none()


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Project]:
    return await list_visible_projects(session, user)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Project:
    if not user.is_service_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the service owner can create projects",
        )
    if payload.code and (
        await session.execute(select(Project).where(Project.code == payload.code))
    ).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Code already exists")
    project = Project(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        status=ProjectStatus.open,
        created_by=user.id,
    )
    session.add(project)
    await session.flush()
    membership = ProjectMembership(project_id=project.id, user_id=user.id, is_owner=True)
    session.add(membership)
    await session.flush()
    session.add(
        MembershipRole(
            membership_id=membership.id,
            role_code=RoleCode.admin,
            project_id=project.id,
        )
    )
    await record(
        session,
        actor_user_id=user.id,
        action="project.create",
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
    )
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Project:
    project, role = await get_project_role(session, user, project_id)
    if project.status != ProjectStatus.open and role != RoleCode.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Archive is admin-only")
    return project


@router.post("/{project_id}/close", response_model=ProjectOut)
async def close_project(
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> Project:
    project, user, _ = ctx
    project.status = ProjectStatus.closed
    project.closed_at = datetime.now(UTC)
    await record(
        session,
        actor_user_id=user.id,
        action="project.close",
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
    )
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a project with all its content (admin only)."""
    project, actor, _ = ctx
    project_id = project.id

    # Ordered deletion to satisfy non-cascading foreign keys.
    await session.execute(delete(Task).where(Task.project_id == project_id))
    await session.execute(delete(Requirement).where(Requirement.project_id == project_id))
    await session.execute(
        delete(RequirementEpic).where(RequirementEpic.project_id == project_id)
    )
    await session.execute(delete(Comment).where(Comment.project_id == project_id))
    await session.execute(delete(Meeting).where(Meeting.project_id == project_id))
    await session.execute(delete(Artifact).where(Artifact.project_id == project_id))
    await session.execute(delete(Diagram).where(Diagram.project_id == project_id))
    await session.execute(delete(Stakeholder).where(Stakeholder.project_id == project_id))
    await session.execute(delete(Employee).where(Employee.project_id == project_id))
    await session.execute(
        delete(ProjectMembership).where(ProjectMembership.project_id == project_id)
    )
    # Keep audit history but detach it from the removed project.
    await session.execute(
        update(AuditLog).where(AuditLog.project_id == project_id).values(project_id=None)
    )
    await session.delete(project)
    await session.commit()


@router.get("/{project_id}/members", response_model=list[MemberOut])
async def list_members(
    ctx: tuple[Project, User, RoleCode] = Depends(
        require_project_role(RoleCode.admin, RoleCode.system_analyst, RoleCode.employee)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[MemberOut]:
    project, _, _ = ctx
    memberships = list(
        (
            await session.execute(
                select(ProjectMembership).where(ProjectMembership.project_id == project.id)
            )
        )
        .scalars()
        .all()
    )
    roles_map: dict[uuid.UUID, list[RoleCode]] = {}
    membership_ids = [m.id for m in memberships]
    if membership_ids:
        rows = (
            await session.execute(
                select(MembershipRole.membership_id, MembershipRole.role_code).where(
                    MembershipRole.membership_id.in_(membership_ids)
                )
            )
        ).all()
        for membership_id, role_code in rows:
            roles_map.setdefault(membership_id, []).append(role_code)
    return [
        MemberOut(
            id=m.id,
            project_id=m.project_id,
            user_id=m.user_id,
            is_owner=m.is_owner,
            joined_at=m.joined_at,
            roles=roles_map.get(m.id, []),
        )
        for m in memberships
    ]


@router.post(
    "/{project_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED
)
async def add_member(
    payload: MemberAdd,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> MemberOut:
    project, actor, _ = ctx
    if await session.get(User, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = (
        await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project.id,
                ProjectMembership.user_id == payload.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")
    roles = _validate_roles([payload.role])
    if RoleCode.system_analyst in roles and await _find_analyst_membership(session, project.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Project already has an analyst"
        )
    membership = ProjectMembership(project_id=project.id, user_id=payload.user_id)
    session.add(membership)
    await session.flush()
    await _replace_roles(session, membership, roles)
    await record(
        session,
        actor_user_id=actor.id,
        action="project.member.add",
        project_id=project.id,
        entity_type="membership",
        entity_id=membership.id,
        after={"user_id": str(payload.user_id), "roles": [r.value for r in roles]},
    )
    await session.commit()
    await session.refresh(membership)
    return MemberOut(
        id=membership.id,
        project_id=membership.project_id,
        user_id=membership.user_id,
        is_owner=membership.is_owner,
        joined_at=membership.joined_at,
        roles=roles,
    )


@router.put("/{project_id}/members/{membership_id}/roles", response_model=MemberOut)
async def set_member_roles(
    membership_id: uuid.UUID,
    payload: MemberRolesUpdate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> MemberOut:
    project, actor, _ = ctx
    membership = await session.get(ProjectMembership, membership_id)
    if membership is None or membership.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    roles = _validate_roles(payload.roles)
    if membership.is_owner and RoleCode.admin not in roles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Owner must keep the admin role"
        )
    if RoleCode.system_analyst in roles:
        current = await _find_analyst_membership(session, project.id)
        if current is not None and current.id != membership.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Project already has an analyst"
            )
    before = await _roles_of(session, membership.id)
    await _replace_roles(session, membership, roles)
    await record(
        session,
        actor_user_id=actor.id,
        action="project.member.roles",
        project_id=project.id,
        entity_type="membership",
        entity_id=membership.id,
        before={"roles": [r.value for r in before]},
        after={"roles": [r.value for r in roles]},
    )
    await session.commit()
    return MemberOut(
        id=membership.id,
        project_id=membership.project_id,
        user_id=membership.user_id,
        is_owner=membership.is_owner,
        joined_at=membership.joined_at,
        roles=roles,
    )


@router.delete("/{project_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    membership_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, actor, _ = ctx
    membership = await session.get(ProjectMembership, membership_id)
    if membership is None or membership.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    if membership.is_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Owner membership cannot be removed"
        )
    await session.delete(membership)
    await record(
        session,
        actor_user_id=actor.id,
        action="project.member.remove",
        project_id=project.id,
        entity_type="membership",
        entity_id=membership_id,
    )
    await session.commit()


@router.post("/{project_id}/analyst/transfer", response_model=MemberOut)
async def transfer_analyst(
    payload: TransferAnalystRequest,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> MemberOut:
    project, actor, _ = ctx
    target = (
        await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project.id,
                ProjectMembership.user_id == payload.user_id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user is not a project member",
        )
    current = await _find_analyst_membership(session, project.id)
    if current is not None and current.id == target.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already the analyst")
    if current is not None:
        await session.execute(
            delete(MembershipRole).where(
                MembershipRole.membership_id == current.id,
                MembershipRole.role_code == RoleCode.system_analyst,
            )
        )
    target_roles = await _roles_of(session, target.id)
    new_roles = [RoleCode.system_analyst]
    if RoleCode.admin in target_roles:
        new_roles = [RoleCode.admin, RoleCode.system_analyst]
    await _replace_roles(session, target, _validate_roles(new_roles))
    await record(
        session,
        actor_user_id=actor.id,
        action="project.analyst.transfer",
        project_id=project.id,
        entity_type="membership",
        entity_id=target.id,
        after={"user_id": str(target.user_id)},
    )
    await session.commit()
    return MemberOut(
        id=target.id,
        project_id=target.project_id,
        user_id=target.user_id,
        is_owner=target.is_owner,
        joined_at=target.joined_at,
        roles=await _roles_of(session, target.id),
    )
