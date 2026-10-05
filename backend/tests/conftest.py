"""Test configuration.

Tests run against a dedicated database (``<name>_test``) created on the fly,
so they never touch the development database. The database URL is redirected
* before* any app module imports the engine.
"""

import asyncio
import os
import subprocess
import sys
import urllib.parse as urlparse
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_DIR = Path(__file__).resolve().parents[1]

from app.core.config import Settings  # noqa: E402

_base = Settings()
_parsed = urlparse.urlparse(_base.database_url.replace("+asyncpg", ""))
TEST_DB_NAME = f"{_parsed.path.lstrip('/')}_test"
TEST_DATABASE_URL = _base.database_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"

from app.db.session import SessionFactory, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.bootstrap import bootstrap  # noqa: E402


def _ensure_test_database() -> None:
    dsn = (
        f"postgresql://{_parsed.username}:{_parsed.password}"
        f"@{_parsed.hostname}:{_parsed.port}/postgres"
    )

    async def create() -> None:
        conn = await asyncpg.connect(dsn)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
        finally:
            await conn.close()

    asyncio.run(create())


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    _ensure_test_database()
    alembic = str(Path(sys.executable).parent / "alembic")
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    subprocess.run([alembic, "upgrade", "head"], cwd=BACKEND_DIR, env=env, check=True)


async def _truncate_all() -> None:
    async with engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
        ).scalars().all()
        if tables:
            quoted = ", ".join(f'"{name}"' for name in tables)
            await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


_initialized = False


@pytest_asyncio.fixture(autouse=True)
async def _clean_database() -> AsyncIterator[None]:
    global _initialized
    if not _initialized:
        await _truncate_all()
        await bootstrap()
        _initialized = True
    yield


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    from app.db.session import get_session

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def _register_and_login(
    client: AsyncClient, login: str, password: str = "password123"
) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={
            "login": login,
            "password": password,
            "last_name": "Тест",
            "first_name": "Тест",
            "middle_name": "Тестович",
        },
    )
    response = await client.post("/auth/login", json={"login": login, "password": password})
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
