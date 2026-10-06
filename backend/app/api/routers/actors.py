"""Project actors: employees (incl. vacant) and stakeholders (incl. abstract)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_role
from app.core.enums import RoleCode
from app.db.session import get_session
from app.models import Employee, EmployeePosition, Position, Project, Stakeholder, User
from app.schemas.actor import (
    EmployeeCreate,
    EmployeeOut,
    LinkUserRequest,
    PositionAssignment,
    StakeholderCreate,
    StakeholderOut,
)
from app.schemas.reference import PositionOut

router = APIRouter(prefix="/projects/{project_id}", tags=["actors"])

_MANAGE = (RoleCode.admin, RoleCode.system_analyst)
_VIEW = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee, RoleCode.guest)


async def _get_or_create_employee(
    session: AsyncSession, project_id: uuid.UUID, user: User, actor_id: uuid.UUID
) -> Employee:
    employee = (
        await session.execute(
            select(Employee).where(
                Employee.project_id == project_id, Employee.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if employee is not None:
        return employee
    employee = Employee(
        project_id=project_id,
        user_id=user.id,
        last_name=user.last_name,
        first_name=user.first_name,
        middle_name=user.middle_name,
        created_by=actor_id,
    )
    session.add(employee)
    await session.flush()
    return employee


async def _position_or_404(session: AsyncSession, position_id: uuid.UUID) -> Position:
    position = await session.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position


# ----------------------------- Employees -----------------------------
@router.get("/employees", response_model=list[EmployeeOut])
async def list_employees(
    limit: int = 200,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Employee]:
    project, _, _ = ctx
    return list(
        (
            await session.execute(
                select(Employee)
                .where(Employee.project_id == project.id)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Employee:
    project, actor, _ = ctx
    if payload.user_id is not None:
        user = await session.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return await _get_or_create_employee(session, project.id, user, actor.id)
    if not payload.first_name and not payload.last_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vacant position requires a name",
        )
    employee = Employee(
        project_id=project.id,
        user_id=None,
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        created_by=actor.id,
    )
    session.add(employee)
    await session.commit()
    await session.refresh(employee)
    return employee


@router.post("/employees/{employee_id}/link", response_model=EmployeeOut)
async def link_employee_user(
    employee_id: uuid.UUID,
    payload: LinkUserRequest,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Employee:
    project, actor, _ = ctx
    employee = await session.get(Employee, employee_id)
    if employee is None or employee.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if payload.user_id is None:
        # Unlink -> vacant position; tasks stay with the employee.
        employee.user_id = None
        await session.commit()
        await session.refresh(employee)
        return employee
    user = await session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    clash = (
        await session.execute(
            select(Employee).where(
                Employee.project_id == project.id,
                Employee.user_id == user.id,
                Employee.id != employee.id,
            )
        )
    ).scalar_one_or_none()
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has an employee in this project",
        )
    employee.user_id = user.id
    employee.last_name = user.last_name
    employee.first_name = user.first_name
    employee.middle_name = user.middle_name
    await session.commit()
    await session.refresh(employee)
    return employee


@router.get("/employees/{employee_id}/positions", response_model=list[PositionOut])
async def list_employee_positions(
    employee_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Position]:
    project, _, _ = ctx
    employee = await session.get(Employee, employee_id)
    if employee is None or employee.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    position_ids = select(EmployeePosition.position_id).where(
        EmployeePosition.employee_id == employee_id
    )
    return list(
        (await session.execute(select(Position).where(Position.id.in_(position_ids))))
        .scalars()
        .all()
    )


@router.post("/employees/{employee_id}/positions", response_model=EmployeeOut)
async def add_employee_position(
    employee_id: uuid.UUID,
    payload: PositionAssignment,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Employee:
    project, actor, _ = ctx
    employee = await session.get(Employee, employee_id)
    if employee is None or employee.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await _position_or_404(session, payload.position_id)
    exists = await session.get(EmployeePosition, (employee.id, payload.position_id))
    if exists is None:
        session.add(
            EmployeePosition(
                employee_id=employee.id,
                position_id=payload.position_id,
                assigned_by=actor.id,
            )
        )
        await session.commit()
    return employee


@router.delete(
    "/employees/{employee_id}/positions/{position_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_employee_position(
    employee_id: uuid.UUID,
    position_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    employee = await session.get(Employee, employee_id)
    if employee is None or employee.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    link = await session.get(EmployeePosition, (employee_id, position_id))
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Position assignment not found"
        )
    await session.delete(link)
    await session.commit()


# ----------------------------- Stakeholders -----------------------------
@router.get("/stakeholders", response_model=list[StakeholderOut])
async def list_stakeholders(
    limit: int = 200,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Stakeholder]:
    project, _, _ = ctx
    return list(
        (
            await session.execute(
                select(Stakeholder)
                .where(Stakeholder.project_id == project.id)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post("/stakeholders", response_model=StakeholderOut, status_code=status.HTTP_201_CREATED)
async def create_stakeholder(
    payload: StakeholderCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Stakeholder:
    project, actor, _ = ctx
    await _position_or_404(session, payload.position_id)
    data = payload.model_dump()
    user_id = data.get("user_id")
    if user_id is not None:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        data.setdefault("last_name", user.last_name)
        data.setdefault("first_name", user.first_name)
        data.setdefault("middle_name", user.middle_name)
    stakeholder = Stakeholder(project_id=project.id, created_by=actor.id, **data)
    session.add(stakeholder)
    await session.commit()
    await session.refresh(stakeholder)
    return stakeholder


@router.post("/stakeholders/{stakeholder_id}/link", response_model=StakeholderOut)
async def link_stakeholder_user(
    stakeholder_id: uuid.UUID,
    payload: LinkUserRequest,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Stakeholder:
    project, _, _ = ctx
    stakeholder = await session.get(Stakeholder, stakeholder_id)
    if stakeholder is None or stakeholder.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stakeholder not found"
        )
    if payload.user_id is None:
        # Unlink -> abstract stakeholder.
        stakeholder.user_id = None
        await session.commit()
        await session.refresh(stakeholder)
        return stakeholder
    user = await session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    stakeholder.user_id = user.id
    stakeholder.last_name = user.last_name
    stakeholder.first_name = user.first_name
    stakeholder.middle_name = user.middle_name
    await session.commit()
    await session.refresh(stakeholder)
    return stakeholder
