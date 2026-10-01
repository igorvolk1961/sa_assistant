from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.session import get_session
from app.main import app
from app.services.bootstrap import bootstrap

_settings = get_settings()
_engine = create_async_engine(_settings.database_url, pool_pre_ping=True)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _bootstrap() -> AsyncIterator[None]:
    await bootstrap()
    yield


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with _Session() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
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
