import uuid

from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import _auth, _register_and_login

settings = get_settings()


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


async def _owner_token(client: AsyncClient) -> str:
    response = await client.post(
        "/auth/login",
        json={
            "login": settings.bootstrap_owner_login,
            "password": settings.bootstrap_owner_password,
        },
    )
    return response.json()["access_token"]


async def _user_id(client: AsyncClient, token: str) -> str:
    me = await client.get("/auth/me", headers=_auth(token))
    return me.json()["id"]


async def _setup(client: AsyncClient) -> dict:
    """Owner + project + position + employee member + stakeholder + requirement."""
    owner = await _owner_token(client)
    project_id = (
        await client.post(
            "/projects", json={"name": f"Проект {_suffix()}"}, headers=_auth(owner)
        )
    ).json()["id"]

    position_id = (
        await client.post(
            "/admin/positions",
            json={"code": f"arch_{_suffix()}", "name": "Архитектор"},
            headers=_auth(owner),
        )
    ).json()["id"]

    worker = await _register_and_login(client, f"work_{_suffix()}")
    worker_id = await _user_id(client, worker["access_token"])
    await client.post(
        f"/projects/{project_id}/members",
        json={"user_id": worker_id, "role": "employee"},
        headers=_auth(owner),
    )
    employee_id = (
        await client.post(
            f"/projects/{project_id}/employees",
            json={"user_id": worker_id},
            headers=_auth(owner),
        )
    ).json()["id"]
    await client.post(
        f"/projects/{project_id}/employees/{employee_id}/positions",
        json={"position_id": position_id},
        headers=_auth(owner),
    )
    await client.post(
        "/admin/mandatory-questions",
        json={"position_id": position_id, "text": "Какие цели проекта?", "sort_order": 1},
        headers=_auth(owner),
    )
    stakeholder_id = (
        await client.post(
            f"/projects/{project_id}/stakeholders",
            json={"position_id": position_id, "organization": "Клиент"},
            headers=_auth(owner),
        )
    ).json()["id"]
    requirement_id = (
        await client.post(
            f"/projects/{project_id}/requirements",
            json={
                "stakeholder_id": stakeholder_id,
                "type": "functional",
                "title": "Регистрация",
                "short_description": "Пользователь должен регистрироваться",
            },
            headers=_auth(owner),
        )
    ).json()["id"]
    return {
        "owner": owner,
        "project_id": project_id,
        "position_id": position_id,
        "worker": worker,
        "worker_id": worker_id,
        "employee_id": employee_id,
        "stakeholder_id": stakeholder_id,
        "requirement_id": requirement_id,
    }


async def test_task_requires_requirement_and_numbering(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]

    bad = await client.post(
        f"/projects/{project_id}/tasks",
        json={
            "requirement_id": str(uuid.uuid4()),
            "type": "feature",
            "short_description": "x",
        },
        headers=_auth(s["owner"]),
    )
    assert bad.status_code == 422

    first = await client.post(
        f"/projects/{project_id}/tasks",
        json={
            "requirement_id": s["requirement_id"],
            "type": "feature",
            "short_description": "Собрать требования",
        },
        headers=_auth(s["owner"]),
    )
    assert first.status_code == 201, first.text
    assert first.json()["number"] == 1
    assert first.json()["status"] == "open"

    second = await client.post(
        f"/projects/{project_id}/tasks",
        json={
            "requirement_id": s["requirement_id"],
            "type": "analysis",
            "short_description": "Изучить предметную область",
        },
        headers=_auth(s["owner"]),
    )
    assert second.json()["number"] == 2


async def test_subtask_and_assignment_and_my_tasks(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    parent = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "feature",
                "short_description": "Родительская задача",
            },
            headers=_auth(s["owner"]),
        )
    ).json()

    child = await client.post(
        f"/projects/{project_id}/tasks",
        json={
            "requirement_id": s["requirement_id"],
            "type": "testing",
            "short_description": "Подзадача",
            "parent_task_id": parent["id"],
            "assignee_employee_ids": [s["employee_id"]],
        },
        headers=_auth(s["owner"]),
    )
    assert child.status_code == 201, child.text
    assert child.json()["parent_task_id"] == parent["id"]

    my = await client.get(
        f"/projects/{project_id}/my-tasks",
        headers=_auth(s["worker"]["access_token"]),
    )
    assert my.status_code == 200
    assert any(t["id"] == child.json()["id"] for t in my.json())

    filtered = await client.get(
        f"/projects/{project_id}/my-tasks",
        params={"status_filter": "in_progress"},
        headers=_auth(s["worker"]["access_token"]),
    )
    assert filtered.status_code == 200


async def test_dependency_cycle_prevented(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]

    async def make_task(text: str) -> str:
        return (
            await client.post(
                f"/projects/{project_id}/tasks",
                json={
                    "requirement_id": s["requirement_id"],
                    "type": "feature",
                    "short_description": text,
                },
                headers=_auth(s["owner"]),
            )
        ).json()["id"]

    a = await make_task("A")
    b = await make_task("B")
    await client.post(
        f"/projects/{project_id}/tasks/{a}/dependencies",
        json={"depends_on_task_id": b},
        headers=_auth(s["owner"]),
    )
    cycle = await client.post(
        f"/projects/{project_id}/tasks/{b}/dependencies",
        json={"depends_on_task_id": a},
        headers=_auth(s["owner"]),
    )
    assert cycle.status_code == 409

    dependents = await client.get(
        f"/projects/{project_id}/tasks/{b}/dependents", headers=_auth(s["owner"])
    )
    assert any(t["id"] == a for t in dependents.json())


async def test_analysis_review_cycle(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    task = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "analysis",
                "short_description": "Сбор информации",
                "assignee_employee_ids": [s["employee_id"]],
            },
            headers=_auth(s["owner"]),
        )
    ).json()

    submit = await client.post(
        f"/projects/{project_id}/tasks/{task['id']}/submit",
        json={"result_text": "Собрал данные"},
        headers=_auth(s["worker"]["access_token"]),
    )
    assert submit.status_code == 200, submit.text
    assert submit.json()["status"] == "on_review"

    no_comment = await client.post(
        f"/projects/{project_id}/tasks/{task['id']}/review",
        json={"accept": False},
        headers=_auth(s["owner"]),
    )
    assert no_comment.status_code == 422

    rejected = await client.post(
        f"/projects/{project_id}/tasks/{task['id']}/review",
        json={"accept": False, "comment": "Мало данных"},
        headers=_auth(s["owner"]),
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    await client.post(
        f"/projects/{project_id}/tasks/{task['id']}/submit",
        json={"result_text": "Дополнил"},
        headers=_auth(s["worker"]["access_token"]),
    )
    accepted = await client.post(
        f"/projects/{project_id}/tasks/{task['id']}/review",
        json={"accept": True},
        headers=_auth(s["owner"]),
    )
    assert accepted.json()["status"] == "completed"

    versions = await client.get(
        f"/projects/{project_id}/tasks/{task['id']}/versions", headers=_auth(s["owner"])
    )
    assert len(versions.json()) == 2


async def test_non_analysis_task_has_no_review(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    task = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "feature",
                "short_description": "Не анализ",
            },
            headers=_auth(s["owner"]),
        )
    ).json()
    response = await client.post(
        f"/projects/{project_id}/tasks/{task['id']}/submit",
        json={"result_text": "x"},
        headers=_auth(s["worker"]["access_token"]),
    )
    assert response.status_code == 409


async def test_guest_comment_and_admin_soft_delete(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    task_id = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "feature",
                "short_description": "Задача с комментарием",
            },
            headers=_auth(s["owner"]),
        )
    ).json()["id"]

    guest = await _register_and_login(client, f"guest_{_suffix()}")
    created = await client.post(
        f"/projects/{project_id}/comments",
        json={"entity_type": "task", "entity_id": task_id, "body": "Комментарий гостя"},
        headers=_auth(guest["access_token"]),
    )
    assert created.status_code == 201, created.text
    assert created.json()["author_role_snapshot"] == "guest"

    listed = await client.get(
        f"/projects/{project_id}/comments",
        params={"entity_type": "task", "entity_id": task_id},
        headers=_auth(guest["access_token"]),
    )
    assert len(listed.json()) == 1

    deleted = await client.delete(
        f"/projects/{project_id}/comments/{created.json()['id']}", headers=_auth(s["owner"])
    )
    assert deleted.status_code == 204
    after = await client.get(
        f"/projects/{project_id}/comments",
        params={"entity_type": "task", "entity_id": task_id},
        headers=_auth(guest["access_token"]),
    )
    assert after.json() == []


async def test_meeting_journal_and_question_coverage(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    meeting = (
        await client.post(
            f"/projects/{project_id}/meetings",
            json={"title": "Первичная беседа", "stakeholder_id": s["stakeholder_id"]},
            headers=_auth(s["owner"]),
        )
    ).json()
    meeting_id = meeting["id"]

    unanswered = await client.get(
        f"/projects/{project_id}/meetings/{meeting_id}/unanswered-questions",
        headers=_auth(s["owner"]),
    )
    assert unanswered.status_code == 200
    assert len(unanswered.json()) == 1
    question_id = unanswered.json()[0]["question_id"]

    segment = await client.post(
        f"/projects/{project_id}/meetings/{meeting_id}/segments",
        json={"text": "Цель — автоматизировать учёт", "speaker_label": "Стейкхолдер"},
        headers=_auth(s["owner"]),
    )
    assert segment.status_code == 201, segment.text

    linked = await client.post(
        f"/projects/{project_id}/meetings/{meeting_id}/segments/{segment.json()['id']}/questions",
        json={"question_id": question_id},
        headers=_auth(s["owner"]),
    )
    assert linked.status_code == 204

    remaining = await client.get(
        f"/projects/{project_id}/meetings/{meeting_id}/unanswered-questions",
        headers=_auth(s["owner"]),
    )
    assert remaining.json() == []


async def test_external_transcript_import(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    meeting_id = (
        await client.post(
            f"/projects/{project_id}/meetings",
            json={"title": "Импорт", "stakeholder_id": s["stakeholder_id"]},
            headers=_auth(s["owner"]),
        )
    ).json()["id"]

    response = await client.post(
        f"/projects/{project_id}/meetings/{meeting_id}/files",
        data={
            "kind": "transcript",
            "source": "telemost",
            "transcript_text": "Реплика 1\nРеплика 2",
        },
        files={"file": ("transcript.txt", "Реплика 1\nРеплика 2".encode(), "text/plain")},
        headers=_auth(s["owner"]),
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "telemost"

    segments = await client.get(
        f"/projects/{project_id}/meetings/{meeting_id}/segments", headers=_auth(s["owner"])
    )
    assert len(segments.json()) == 2
    assert segments.json()[0]["source"] == "external"


async def test_analysis_status_cannot_bypass_review(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    task = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "analysis",
                "short_description": "Анализ",
            },
            headers=_auth(s["owner"]),
        )
    ).json()
    response = await client.patch(
        f"/projects/{project_id}/tasks/{task['id']}",
        json={"status": "completed"},
        headers=_auth(s["owner"]),
    )
    assert response.status_code == 409


async def test_review_requires_analysis_and_on_review(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    feature = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "feature",
                "short_description": "Не анализ",
            },
            headers=_auth(s["owner"]),
        )
    ).json()
    response = await client.post(
        f"/projects/{project_id}/tasks/{feature['id']}/review",
        json={"accept": True},
        headers=_auth(s["owner"]),
    )
    assert response.status_code == 409


async def test_deleted_comments_hidden_from_non_admin(client: AsyncClient) -> None:
    s = await _setup(client)
    project_id = s["project_id"]
    task_id = (
        await client.post(
            f"/projects/{project_id}/tasks",
            json={
                "requirement_id": s["requirement_id"],
                "type": "feature",
                "short_description": "x",
            },
            headers=_auth(s["owner"]),
        )
    ).json()["id"]
    guest = await _register_and_login(client, f"guest_{_suffix()}")
    comment = (
        await client.post(
            f"/projects/{project_id}/comments",
            json={"entity_type": "task", "entity_id": task_id, "body": "c"},
            headers=_auth(guest["access_token"]),
        )
    ).json()
    await client.delete(
        f"/projects/{project_id}/comments/{comment['id']}", headers=_auth(s["owner"])
    )
    forced = await client.get(
        f"/projects/{project_id}/comments",
        params={"entity_type": "task", "entity_id": task_id, "include_deleted": "true"},
        headers=_auth(guest["access_token"]),
    )
    assert forced.status_code == 403


async def test_cross_project_references_rejected(client: AsyncClient) -> None:
    first = await _setup(client)
    second = await _setup(client)

    meeting = (
        await client.post(
            f"/projects/{first['project_id']}/meetings",
            json={"title": "M", "stakeholder_id": first["stakeholder_id"]},
            headers=_auth(first["owner"]),
        )
    ).json()

    bad_stakeholder = await client.patch(
        f"/projects/{first['project_id']}/meetings/{meeting['id']}",
        json={"stakeholder_id": second["stakeholder_id"]},
        headers=_auth(first["owner"]),
    )
    assert bad_stakeholder.status_code == 422

    other_meeting = (
        await client.post(
            f"/projects/{second['project_id']}/meetings",
            json={"title": "M2", "stakeholder_id": second["stakeholder_id"]},
            headers=_auth(second["owner"]),
        )
    ).json()
    bad_artifact = await client.post(
        f"/projects/{first['project_id']}/artifacts",
        json={"type": "glossary", "content": {}, "meeting_id": other_meeting["id"]},
        headers=_auth(first["owner"]),
    )
    assert bad_artifact.status_code == 422
