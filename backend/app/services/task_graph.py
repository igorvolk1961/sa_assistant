"""Task dependency graph helpers: cycle detection and reachability.

Edges for a project are loaded once and traversed in memory to avoid N+1
queries during validation.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskDependency


async def _edges_by_task(
    session: AsyncSession, project_id: uuid.UUID
) -> dict[uuid.UUID, list[uuid.UUID]]:
    rows = (
        await session.execute(
            select(TaskDependency.task_id, TaskDependency.depends_on_task_id)
            .join(Task, Task.id == TaskDependency.task_id)
            .where(Task.project_id == project_id)
        )
    ).all()
    edges: dict[uuid.UUID, list[uuid.UUID]] = {}
    for task_id, depends_on in rows:
        edges.setdefault(task_id, []).append(depends_on)
    return edges


def _reachable(edges: dict[uuid.UUID, list[uuid.UUID]], start_id: uuid.UUID) -> set[uuid.UUID]:
    visited: set[uuid.UUID] = set()
    stack = [start_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(edges.get(current, []))
    return visited


async def would_create_cycle(
    session: AsyncSession,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
) -> bool:
    """Adding edge ``task -> depends_on`` creates a cycle if ``task`` is reachable
    from ``depends_on`` through existing dependency edges."""
    if task_id == depends_on_task_id:
        return True
    edges = await _edges_by_task(session, project_id)
    return task_id in _reachable(edges, depends_on_task_id)
