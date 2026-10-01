"""Tasks and subtasks: numbering, assignment, dependencies, files, review cycle."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_role
from app.core.enums import Importance, RoleCode, TaskStatus, TaskType
from app.db.session import get_session
from app.models import (
    Employee,
    MembershipRole,
    Project,
    ProjectMembership,
    Requirement,
    Task,
    TaskAssignment,
    TaskAttachment,
    TaskDependency,
    TaskResultVersion,
    User,
)
from app.schemas.task import (
    AssignmentCreate,
    DependencyCreate,
    ReviewRequest,
    SubmitRequest,
    TaskAssignmentOut,
    TaskAttachmentOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.services.access import ensure_all_in_project, ensure_in_project
from app.services.files import file_response
from app.services.notifications import notify
from app.services.storage import LocalStorage, get_storage
from app.services.task_graph import would_create_cycle

router = APIRouter(prefix="/projects/{project_id}", tags=["tasks"])

_VIEW = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee, RoleCode.guest)
_EDIT = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee)
_MANAGE = (RoleCode.admin, RoleCode.system_analyst)


async def _task_or_404(
    session: AsyncSession, project_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    task = await session.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _require_in_project(
    session: AsyncSession, project_id: uuid.UUID, model, ref_id: uuid.UUID, name: str
):
    return await ensure_in_project(session, project_id, model, ref_id, name)


async def _next_number(session: AsyncSession, project_id: uuid.UUID) -> int:
    current = (
        await session.execute(
            select(func.max(Task.number)).where(Task.project_id == project_id)
        )
    ).scalar_one_or_none()
    return (current or 0) + 1


async def _assignee_user_ids(session: AsyncSession, task_id: uuid.UUID) -> list[uuid.UUID]:
    rows = (
        await session.execute(
            select(Employee.user_id)
            .join(TaskAssignment, TaskAssignment.employee_id == Employee.id)
            .where(TaskAssignment.task_id == task_id, Employee.user_id.is_not(None))
        )
    ).scalars().all()
    return [uid for uid in rows if uid is not None]


async def _analyst_user_ids(session: AsyncSession, project_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        (
            await session.execute(
                select(ProjectMembership.user_id)
                .join(MembershipRole, MembershipRole.membership_id == ProjectMembership.id)
                .where(
                    ProjectMembership.project_id == project_id,
                    MembershipRole.role_code == RoleCode.system_analyst,
                )
            )
        )
        .scalars()
        .all()
    )


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    status_filter: TaskStatus | None = None,
    importance: Importance | None = None,
    requirement_id: uuid.UUID | None = None,
    parent_task_id: uuid.UUID | None = None,
    assignee_employee_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Task]:
    project, _, _ = ctx
    stmt = select(Task).where(Task.project_id == project.id)
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    if importance is not None:
        stmt = stmt.where(Task.importance == importance)
    if requirement_id is not None:
        stmt = stmt.where(Task.requirement_id == requirement_id)
    if parent_task_id is not None:
        stmt = stmt.where(Task.parent_task_id == parent_task_id)
    if assignee_employee_id is not None:
        stmt = stmt.where(
            Task.id.in_(
                select(TaskAssignment.task_id).where(
                    TaskAssignment.employee_id == assignee_employee_id,
                    TaskAssignment.unassigned_at.is_(None),
                )
            )
        )
    return list(
        (await session.execute(stmt.order_by(Task.number).limit(limit).offset(offset)))
        .scalars()
        .all()
    )


@router.get("/my-tasks", response_model=list[TaskOut])
async def my_tasks(
    status_filter: TaskStatus | None = None,
    importance: Importance | None = None,
    limit: int = 100,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Task]:
    project, actor, _ = ctx
    my_employee_ids = select(Employee.id).where(
        Employee.project_id == project.id, Employee.user_id == actor.id
    )
    assigned = select(TaskAssignment.task_id).where(
        TaskAssignment.employee_id.in_(my_employee_ids),
        TaskAssignment.unassigned_at.is_(None),
    )
    stmt = (
        select(Task)
        .where(
            Task.project_id == project.id,
            or_(Task.id.in_(assigned), Task.created_by == actor.id),
        )
        .order_by(Task.number)
    )
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    if importance is not None:
        stmt = stmt.where(Task.importance == importance)
    return list(
        (await session.execute(stmt.limit(limit).offset(offset))).scalars().all()
    )


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Task:
    project, actor, _ = ctx
    await _require_in_project(
        session, project.id, Requirement, payload.requirement_id, "Requirement"
    )
    if payload.parent_task_id is not None:
        await _require_in_project(
            session, project.id, Task, payload.parent_task_id, "Parent task"
        )
    await ensure_all_in_project(
        session, project.id, Employee, payload.assignee_employee_ids, "Employee"
    )
    await ensure_all_in_project(
        session, project.id, Task, payload.depends_on_task_ids, "Dependency task"
    )
    task = Task(
        project_id=project.id,
        number=await _next_number(session, project.id),
        parent_task_id=payload.parent_task_id,
        requirement_id=payload.requirement_id,
        type=payload.type,
        importance=payload.importance,
        status=TaskStatus.open,
        short_description=payload.short_description,
        description=payload.description,
        prompt=payload.prompt,
        due_at=payload.due_at,
        created_by=actor.id,
    )
    session.add(task)
    await session.flush()
    for employee_id in payload.assignee_employee_ids:
        session.add(
            TaskAssignment(task_id=task.id, employee_id=employee_id, assigned_by=actor.id)
        )
    for dep_id in payload.depends_on_task_ids:
        session.add(TaskDependency(task_id=task.id, depends_on_task_id=dep_id))
    for user_id in await _assignee_user_ids(session, task.id):
        notify(
            session,
            user_id=user_id,
            type_="task.assigned",
            payload={"task_id": str(task.id), "number": task.number},
        )
    await session.commit()
    await session.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> Task:
    project, _, _ = ctx
    return await _task_or_404(session, project.id, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> Task:
    project, _, _ = ctx
    task = await _task_or_404(session, project.id, task_id)
    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status")
    if (
        new_status is not None
        and task.type == TaskType.analysis
        and new_status
        in (TaskStatus.on_review, TaskStatus.completed, TaskStatus.rejected)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis tasks change these statuses via submit/review only",
        )
    if "requirement_id" in data and data["requirement_id"] is not None:
        await _require_in_project(
            session, project.id, Requirement, data["requirement_id"], "Requirement"
        )
    for field, value in data.items():
        setattr(task, field, value)
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    task = await _task_or_404(session, project.id, task_id)
    await session.delete(task)
    await session.commit()


# ----------------------------- Assignments -----------------------------
@router.get("/tasks/{task_id}/assignments", response_model=list[TaskAssignmentOut])
async def list_assignments(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[TaskAssignment]:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    return list(
        (
            await session.execute(
                select(TaskAssignment).where(
                    TaskAssignment.task_id == task_id,
                    TaskAssignment.unassigned_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )


@router.post("/tasks/{task_id}/assignments", status_code=status.HTTP_204_NO_CONTENT)
async def assign_task(
    task_id: uuid.UUID,
    payload: AssignmentCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, actor, _ = ctx
    task = await _task_or_404(session, project.id, task_id)
    employee = await _require_in_project(
        session, project.id, Employee, payload.employee_id, "Employee"
    )
    existing = (
        await session.execute(
            select(TaskAssignment).where(
                TaskAssignment.task_id == task_id,
                TaskAssignment.employee_id == employee.id,
                TaskAssignment.unassigned_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            TaskAssignment(task_id=task.id, employee_id=employee.id, assigned_by=actor.id)
        )
    if task.status == TaskStatus.open:
        task.status = TaskStatus.in_progress
    notify(
        session,
        user_id=employee.user_id,
        type_="task.assigned",
        payload={"task_id": str(task.id), "number": task.number},
    )
    await session.commit()


@router.delete("/tasks/{task_id}/assignments/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_task(
    task_id: uuid.UUID,
    employee_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    assignment = (
        await session.execute(
            select(TaskAssignment).where(
                TaskAssignment.task_id == task_id,
                TaskAssignment.employee_id == employee_id,
                TaskAssignment.unassigned_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    assignment.unassigned_at = datetime.now(UTC)
    await session.commit()


# ----------------------------- Dependencies -----------------------------
@router.get("/tasks/{task_id}/dependencies", response_model=list[TaskOut])
async def list_dependencies(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Task]:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    dep_ids = select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == task_id)
    return list((await session.execute(select(Task).where(Task.id.in_(dep_ids)))).scalars().all())


@router.get("/tasks/{task_id}/dependents", response_model=list[TaskOut])
async def list_dependents(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Task]:
    """Tasks that depend on the completion of this one."""
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    dependent_ids = select(TaskDependency.task_id).where(
        TaskDependency.depends_on_task_id == task_id
    )
    return list(
        (await session.execute(select(Task).where(Task.id.in_(dependent_ids)))).scalars().all()
    )


@router.post("/tasks/{task_id}/dependencies", status_code=status.HTTP_204_NO_CONTENT)
async def add_dependency(
    task_id: uuid.UUID,
    payload: DependencyCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    await _require_in_project(
        session, project.id, Task, payload.depends_on_task_id, "Dependency task"
    )
    if await would_create_cycle(session, project.id, task_id, payload.depends_on_task_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Dependency would create a cycle"
        )
    existing = await session.get(TaskDependency, (task_id, payload.depends_on_task_id))
    if existing is None:
        session.add(
            TaskDependency(task_id=task_id, depends_on_task_id=payload.depends_on_task_id)
        )
        await session.commit()


@router.delete(
    "/tasks/{task_id}/dependencies/{depends_on_task_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_dependency(
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    await session.execute(
        delete(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    await session.commit()


# ----------------------------- Attachments -----------------------------
@router.get("/tasks/{task_id}/attachments", response_model=list[TaskAttachmentOut])
async def list_attachments(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[TaskAttachment]:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    return list(
        (
            await session.execute(
                select(TaskAttachment).where(TaskAttachment.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=TaskAttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
    file: UploadFile = File(...),
) -> TaskAttachment:
    project, actor, _ = ctx
    await _task_or_404(session, project.id, task_id)
    data = await file.read()
    key = await storage.save_async(data, filename=file.filename or "file", prefix="tasks")
    attachment = TaskAttachment(
        task_id=task_id,
        storage_key=key,
        filename=file.filename,
        mime_type=file.content_type,
        size_bytes=len(data),
        uploaded_by=actor.id,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


@router.get("/tasks/{task_id}/attachments/{attachment_id}/content")
async def download_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
) -> Response:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    attachment = await session.get(TaskAttachment, attachment_id)
    if attachment is None or attachment.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return await file_response(
        storage,
        storage_key=attachment.storage_key,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
    )


# ----------------------------- Review cycle (analysis tasks) -----------------------------
@router.post("/tasks/{task_id}/submit", response_model=TaskOut)
async def submit_task(
    task_id: uuid.UUID,
    payload: SubmitRequest,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> Task:
    project, actor, _ = ctx
    task = await _task_or_404(session, project.id, task_id)
    if task.type != TaskType.analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review cycle applies only to analysis tasks",
        )
    if payload.result_text is not None:
        last_version = (
            await session.execute(
                select(func.max(TaskResultVersion.version_no)).where(
                    TaskResultVersion.task_id == task.id
                )
            )
        ).scalar_one_or_none() or 0
        session.add(
            TaskResultVersion(
                task_id=task.id,
                version_no=last_version + 1,
                result_text=payload.result_text,
                submitted_by=actor.id,
                review_status="pending",
            )
        )
    task.status = TaskStatus.on_review
    for user_id in await _analyst_user_ids(session, project.id):
        notify(
            session,
            user_id=user_id,
            type_="task.submitted",
            payload={"task_id": str(task.id), "number": task.number},
        )
    await session.commit()
    await session.refresh(task)
    return task


@router.post("/tasks/{task_id}/review", response_model=TaskOut)
async def review_task(
    task_id: uuid.UUID,
    payload: ReviewRequest,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> Task:
    project, actor, _ = ctx
    task = await _task_or_404(session, project.id, task_id)
    if task.type != TaskType.analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review cycle applies only to analysis tasks",
        )
    if task.status != TaskStatus.on_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is not awaiting review",
        )
    version = (
        await session.execute(
            select(TaskResultVersion)
            .where(TaskResultVersion.task_id == task.id)
            .order_by(TaskResultVersion.version_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if payload.accept:
        task.status = TaskStatus.completed
        if version is not None:
            version.review_status = "accepted"
    else:
        if not payload.comment or not payload.comment.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Rejection requires a comment",
            )
        task.status = TaskStatus.rejected
        if version is not None:
            version.review_status = "rejected"
            version.review_comment = payload.comment
        else:
            session.add(
                TaskResultVersion(
                    task_id=task.id,
                    version_no=1,
                    submitted_by=actor.id,
                    review_status="rejected",
                    review_comment=payload.comment,
                )
            )
    for user_id in await _assignee_user_ids(session, task.id):
        notify(
            session,
            user_id=user_id,
            type_="task.reviewed",
            payload={
                "task_id": str(task.id),
                "number": task.number,
                "accepted": payload.accept,
            },
        )
    await session.commit()
    await session.refresh(task)
    return task


@router.get("/tasks/{task_id}/versions", response_model=list[dict])
async def list_versions(
    task_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    project, _, _ = ctx
    await _task_or_404(session, project.id, task_id)
    versions = list(
        (
            await session.execute(
                select(TaskResultVersion)
                .where(TaskResultVersion.task_id == task_id)
                .order_by(TaskResultVersion.version_no)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(v.id),
            "version_no": v.version_no,
            "result_text": v.result_text,
            "submitted_by": str(v.submitted_by) if v.submitted_by else None,
            "submitted_at": v.submitted_at.isoformat() if v.submitted_at else None,
            "review_status": v.review_status.value if v.review_status else None,
            "review_comment": v.review_comment,
        }
        for v in versions
    ]
