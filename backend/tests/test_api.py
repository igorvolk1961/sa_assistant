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
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def test_register_login_and_me(client: AsyncClient) -> None:
    login = f"user_{_suffix()}"
    tokens = await _register_and_login(client, login)
    assert tokens["access_token"]
    me = await client.get("/auth/me", headers=_auth(tokens["access_token"]))
    assert me.status_code == 200
    body = me.json()
    assert body["login"] == login
    assert body["is_service_owner"] is False


async def test_refresh_token(client: AsyncClient) -> None:
    tokens = await _register_and_login(client, f"user_{_suffix()}")
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


async def test_project_lifecycle_and_visibility(client: AsyncClient) -> None:
    owner = await _owner_token(client)
    guest_tokens = await _register_and_login(client, f"guest_{_suffix()}")
    guest = guest_tokens["access_token"]

    created = await client.post(
        "/projects", json={"name": f"Проект {_suffix()}"}, headers=_auth(owner)
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    listed = await client.get("/projects", headers=_auth(guest))
    assert listed.status_code == 200
    assert any(p["id"] == project_id for p in listed.json())

    closed = await client.post(f"/projects/{project_id}/close", headers=_auth(owner))
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    guest_after = await client.get(f"/projects/{project_id}", headers=_auth(guest))
    assert guest_after.status_code == 403
    owner_after = await client.get(f"/projects/{project_id}", headers=_auth(owner))
    assert owner_after.status_code == 200


async def test_guest_cannot_create_project(client: AsyncClient) -> None:
    guest = (await _register_and_login(client, f"guest_{_suffix()}"))["access_token"]
    response = await client.post("/projects", json={"name": "x"}, headers=_auth(guest))
    assert response.status_code == 403


async def test_analyst_uniqueness_and_transfer(client: AsyncClient) -> None:
    owner = await _owner_token(client)
    project_id = (
        await client.post(
            "/projects", json={"name": f"Проект {_suffix()}"}, headers=_auth(owner)
        )
    ).json()["id"]

    first = await _register_and_login(client, f"an1_{_suffix()}")
    second = await _register_and_login(client, f"an2_{_suffix()}")

    first_me = (await client.get("/auth/me", headers=_auth(first["access_token"]))).json()
    second_me = (await client.get("/auth/me", headers=_auth(second["access_token"]))).json()

    added = await client.post(
        f"/projects/{project_id}/members",
        json={"user_id": first_me["id"], "role": "system_analyst"},
        headers=_auth(owner),
    )
    assert added.status_code == 201, added.text

    conflict = await client.post(
        f"/projects/{project_id}/members",
        json={"user_id": second_me["id"], "role": "system_analyst"},
        headers=_auth(owner),
    )
    assert conflict.status_code == 409

    await client.post(
        f"/projects/{project_id}/members",
        json={"user_id": second_me["id"], "role": "employee"},
        headers=_auth(owner),
    )
    transferred = await client.post(
        f"/projects/{project_id}/analyst/transfer",
        json={"user_id": second_me["id"]},
        headers=_auth(owner),
    )
    assert transferred.status_code == 200, transferred.text
    assert set(transferred.json()["roles"]) == {"system_analyst"}


async def test_owner_cannot_be_demoted(client: AsyncClient) -> None:
    owner = await _owner_token(client)
    project_id = (
        await client.post(
            "/projects", json={"name": f"Проект {_suffix()}"}, headers=_auth(owner)
        )
    ).json()["id"]
    members = (
        await client.get(f"/projects/{project_id}/members", headers=_auth(owner))
    ).json()
    owner_membership = next(m for m in members if m["is_owner"])
    response = await client.put(
        f"/projects/{project_id}/members/{owner_membership['id']}/roles",
        json={"roles": ["system_analyst"]},
        headers=_auth(owner),
    )
    assert response.status_code == 409


async def test_employee_and_stakeholder_linking(client: AsyncClient) -> None:
    owner = await _owner_token(client)
    project_id = (
        await client.post(
            "/projects", json={"name": f"Проект {_suffix()}"}, headers=_auth(owner)
        )
    ).json()["id"]

    position = await client.post(
        "/admin/positions",
        json={"code": f"arch_{_suffix()}", "name": "Архитектор"},
        headers=_auth(owner),
    )
    assert position.status_code == 201, position.text
    position_id = position.json()["id"]

    worker = await _register_and_login(client, f"work_{_suffix()}")
    worker_me = (await client.get("/auth/me", headers=_auth(worker["access_token"]))).json()

    employee = await client.post(
        f"/projects/{project_id}/employees",
        json={"user_id": worker_me["id"]},
        headers=_auth(owner),
    )
    assert employee.status_code == 201, employee.text
    employee_id = employee.json()["id"]
    assert employee.json()["last_name"] == worker_me["last_name"]

    assigned = await client.post(
        f"/projects/{project_id}/employees/{employee_id}/positions",
        json={"position_id": position_id},
        headers=_auth(owner),
    )
    assert assigned.status_code == 200

    unlinked = await client.post(
        f"/projects/{project_id}/employees/{employee_id}/link",
        json={"user_id": None},
        headers=_auth(owner),
    )
    assert unlinked.status_code == 200
    assert unlinked.json()["user_id"] is None

    stakeholder = await client.post(
        f"/projects/{project_id}/stakeholders",
        json={"position_id": position_id},
        headers=_auth(owner),
    )
    assert stakeholder.status_code == 201, stakeholder.text
    assert stakeholder.json()["user_id"] is None
