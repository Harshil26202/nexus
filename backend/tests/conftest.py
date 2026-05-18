"""Test fixtures and configuration."""
import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.redis_client import redis_pool
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncIterator[AsyncClient]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(redis_pool, "get", AsyncMock(return_value=None)), \
         patch.object(redis_pool, "set", AsyncMock()), \
         patch.object(redis_pool, "publish", AsyncMock()), \
         patch.object(redis_pool, "delete", AsyncMock()), \
         patch.object(redis_pool, "invalidate_prefix", AsyncMock()):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for agent tests — patch where it's used, not where it's defined."""
    with patch("app.agents.base.get_openai_client") as mock:
        client = AsyncMock()
        mock.return_value = client

        # Default chat completion response
        choice = MagicMock()
        choice.message.content = '{"summary": "Test analysis", "risk_score": 35, "risk_level": "medium", "categories": ["feature"], "blast_radius": {"services": ["test-service"], "apis": [], "db_schemas": [], "security_surfaces": [], "data_pipelines": []}, "risk_factors": [], "hidden_risks": [], "estimated_test_coverage_needed": [], "deploy_considerations": []}'
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.total_tokens = 450
        client.chat.completions.create = AsyncMock(return_value=resp)

        yield client
