"""Shared fixtures: in-memory SQLite + async HTTP client.

Replaces tests/conftest.py from the Postgres version. Nothing else changes;
tests/auth/* work as-is.

Extra dev dependency:  poetry add --group dev aiosqlite
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.auth.models  # noqa: F401  (register tables on Base.metadata)
import app.users.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    """A brand-new in-memory database for every test (full isolation, no cleanup)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,  # one shared connection, so the in-memory DB persists
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        # SQLite ignores FOREIGN KEY / ON DELETE CASCADE unless this is switched on
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test/api/v1"
    ) as http_client:
        yield http_client
    app.dependency_overrides.clear()
