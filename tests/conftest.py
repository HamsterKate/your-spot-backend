"""Shared fixtures: in-memory SQLite + async HTTP client.

Replaces tests/conftest.py from the Postgres version. Nothing else changes;
tests/auth/* work as-is.

Extra dev dependency:  poetry add --group dev aiosqlite
"""

import pytest
import pytest_asyncio
from uuid import UUID
from datetime import datetime, timedelta, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.auth.models  # noqa: F401  (register tables on Base.metadata)
import app.users.models  # noqa: F401
from app.places.models import CategoryModel, PlaceModel, TagModel
from app.db.base import Base
from app.db.session import get_db
from app.main import app

PASSWORD = "StrongPass123!"
MANY_PLACES_COUNT = 25
MANY_PLACES_BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# Plain helpers (not fixtures)
# --------------------------------------------------------------------------
async def _add_model(db_session, model_cls, **fields):
    """Insert one row and commit it."""
    instance = model_cls(**fields)
    db_session.add(instance)
    await db_session.commit()
    return instance


async def _create_place(client, auth_headers, place_payload, **overrides) -> dict:
    """POST /places with the base payload plus overrides;
    return the JSON body."""
    response = await client.post(
        "/places",
        json={**place_payload, **overrides},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_many_places(
    client,
    auth_headers,
    place_payload,
    db_session,
    name_prefix: str,
    **overrides,
) -> list[dict]:
    """Create MANY_PLACES_COUNT places, oldest first,
    with explicit created_at.

    created_at is set directly in the DB because
    server-generated timestamps can collide, which
    would make the ordering assertions nondeterministic.
    """
    places = []
    for i in range(MANY_PLACES_COUNT):
        created = await _create_place(
            client,
            auth_headers,
            place_payload,
            name=f"{name_prefix} {i}",
            **overrides,
        )
        await db_session.execute(
            update(PlaceModel)
            .where(PlaceModel.id == UUID(created["id"]))
            .values(created_at=MANY_PLACES_BASE_TIME + timedelta(minutes=i))
        )
        places.append(created)
    await db_session.commit()
    return places


# --------------------------------------------------------------------------
# Infrastructure fixtures
# --------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_session():
    """A brand-new in-memory database
    for every test (full isolation, no cleanup)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,  # one shared connection
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        # SQLite ignores FOREIGN KEY / ON DELETE CASCADE
        # unless this is switched on
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


# --------------------------------------------------------------------------
# Auth fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def register_payload() -> dict:
    return {
        "display_name": "Test User",
        "email": "user@example.com",
        "password": PASSWORD,
    }


@pytest_asyncio.fixture
async def registered_user(client, register_payload) -> dict:
    response = await client.post("/auth/register", json=register_payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest_asyncio.fixture
async def tokens(client, registered_user, register_payload) -> dict:
    response = await client.post(
        "/auth/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def auth_headers(tokens) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# --------------------------------------------------------------------------
# Category and tag fixtures
# --------------------------------------------------------------------------
@pytest_asyncio.fixture
async def category_cafe(db_session) -> CategoryModel:
    return await _add_model(db_session, CategoryModel, name="Cafe")


@pytest_asyncio.fixture
async def category_park(db_session) -> CategoryModel:
    return await _add_model(db_session, CategoryModel, name="Park")


@pytest_asyncio.fixture
async def tag_outdoor(db_session) -> TagModel:
    return await _add_model(db_session, TagModel, name="Outdoor")


@pytest_asyncio.fixture
async def tag_wifi(db_session) -> TagModel:
    return await _add_model(db_session, TagModel, name="Wi-Fi")


@pytest_asyncio.fixture
async def tag_pets(db_session) -> TagModel:
    return await _add_model(db_session, TagModel, name="Pet friendly")


# --------------------------------------------------------------------------
# Place fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def place_payload() -> dict:
    return {
        "name": "Test Place",
        "description": "A place used by endpoint tests.",
        "address": "123 Test Street",
    }


@pytest_asyncio.fixture
async def place(client, auth_headers, place_payload) -> dict:
    return await _create_place(client, auth_headers, place_payload)


@pytest_asyncio.fixture
async def searchable_places(
    client, auth_headers, place_payload, place
) -> dict[str, str]:
    names = {
        "park": "Central Park",
        "cafe": "Park Side Cafe",
        "museum": "City Museum",
        "discount": "50% Off Shop",
        "underscore": "a_b Bar",
    }
    ids = {"default": place["id"]}
    for key, name in names.items():
        created = await _create_place(client, auth_headers, place_payload, name=name)
        ids[key] = created["id"]
    return ids


@pytest_asyncio.fixture
async def place_cafe(client, auth_headers, place_payload, category_cafe) -> dict:
    return await _create_place(
        client,
        auth_headers,
        place_payload,
        name="Blue Bottle Coffee",
        category_ids=[str(category_cafe.id)],
    )


@pytest_asyncio.fixture
async def place_park(client, auth_headers, place_payload, category_park) -> dict:
    return await _create_place(
        client,
        auth_headers,
        place_payload,
        name="Central Park",
        category_ids=[str(category_park.id)],
    )


@pytest_asyncio.fixture
async def place_cafe_and_park(
    client, auth_headers, place_payload, category_cafe, category_park
) -> dict:
    return await _create_place(
        client,
        auth_headers,
        place_payload,
        name="Park Cafe",
        category_ids=[str(category_cafe.id), str(category_park.id)],
    )


@pytest_asyncio.fixture
async def many_cafe_places(
    client, auth_headers, place_payload, category_cafe, db_session
) -> list[dict]:
    """25 cafe places, oldest first, with explicit created_at values."""
    return await _create_many_places(
        client,
        auth_headers,
        place_payload,
        db_session,
        name_prefix="Cafe",
        category_ids=[str(category_cafe.id)],
    )


@pytest_asyncio.fixture
async def many_outdoor_places(
    client, auth_headers, place_payload, tag_outdoor, db_session
) -> list[dict]:
    """25 places with the 'Outdoor' tag, oldest first, explicit created_at."""
    return await _create_many_places(
        client,
        auth_headers,
        place_payload,
        db_session,
        name_prefix="Outdoor",
        tag_ids=[str(tag_outdoor.id)],
    )


@pytest_asyncio.fixture
async def tagged_places(
    client, auth_headers, place_payload, tag_outdoor, tag_wifi, tag_pets
) -> dict[str, dict]:
    """Four places covering every tag combination we care about.

    outdoor       -> [outdoor]
    wifi          -> [wifi]
    outdoor_wifi  -> [outdoor, wifi]
    untagged      -> []
    (tag_pets is intentionally unused by any place)
    """
    specs = {
        "outdoor": ("Garden Terrace", [tag_outdoor]),
        "wifi": ("Coworking Hub", [tag_wifi]),
        "outdoor_wifi": ("Rooftop Cafe", [tag_outdoor, tag_wifi]),
        "untagged": ("Plain Place", []),
    }
    return {
        key: await _create_place(
            client,
            auth_headers,
            place_payload,
            name=name,
            tag_ids=[str(tag.id) for tag in tags],
        )
        for key, (name, tags) in specs.items()
    }
