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
from app.core.config import settings
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
def _json_or_fail(response, expected_status) -> dict:
    """Assert the status code (showing the body on failure); return the JSON."""
    assert response.status_code == expected_status, response.text
    return response.json()


def _ids(items) -> list[str]:
    """Model instances -> list of stringified ids, as the API expects."""
    return [str(item.id) for item in items]


async def _register(client, payload) -> dict:
    return _json_or_fail(await client.post("/auth/register", json=payload), 201)


async def _login(client, email, password) -> dict:
    response = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    return _json_or_fail(response, 200)


def _bearer(tokens) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _add_model(db_session, model_cls, **fields):
    """Insert one row and commit it."""
    instance = model_cls(**fields)
    db_session.add(instance)
    await db_session.commit()
    return instance


def _named_model_fixture(fixture_name, model_cls, name):
    """Build a fixture that inserts one `model_cls(name=name)` row."""

    @pytest_asyncio.fixture(name=fixture_name)
    async def _fixture(db_session):
        return await _add_model(db_session, model_cls, name=name)

    return _fixture


# --- ways to look at the same place --------------------------------------
async def _as_created(client, created, viewer, owner):
    return created


async def _as_fetched(client, created, viewer, owner):
    response = await client.get(f"/places/{created['id']}", headers=viewer)
    return _json_or_fail(response, 200)


async def _as_listed(client, created, viewer, owner):
    response = await client.get("/places", headers=viewer)
    body = _json_or_fail(response, 200)
    items = body["items"] if isinstance(body, dict) else body
    return next(item for item in items if item["id"] == created["id"])


async def _as_updated(client, created, viewer, owner):
    # Only the owner may PATCH, so this always uses the owner's headers.
    # It touches an unrelated field, so the field under test must survive a PATCH.
    response = await client.patch(
        f"/places/{created['id']}",
        json={"description": "Changed by the view_place fixture."},
        headers=owner,
    )
    return _json_or_fail(response, 200)


_VIEWS = {
    "created": _as_created,
    "fetched": _as_fetched,
    "listed": _as_listed,
    "updated": _as_updated,
}


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
        transport=ASGITransport(app=app),
        base_url=f"http://test{settings.api_v1_prefix}",
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
    return await _register(client, register_payload)


@pytest_asyncio.fixture
async def tokens(client, registered_user, register_payload) -> dict:
    return await _login(client, register_payload["email"], register_payload["password"])


@pytest.fixture
def auth_headers(tokens) -> dict:
    return _bearer(tokens)


@pytest_asyncio.fixture
async def make_auth_headers(client):
    """Factory: register + log in an extra user, return their auth headers."""

    async def _make(display_name: str, email: str, password: str = PASSWORD) -> dict:
        await _register(
            client,
            {"display_name": display_name, "email": email, "password": password},
        )
        return _bearer(await _login(client, email, password))

    return _make


# --------------------------------------------------------------------------
# Category and tag fixtures
# --------------------------------------------------------------------------
category_cafe = _named_model_fixture("category_cafe", CategoryModel, "Cafe")
category_park = _named_model_fixture("category_park", CategoryModel, "Park")
tag_outdoor = _named_model_fixture("tag_outdoor", TagModel, "Outdoor")
tag_wifi = _named_model_fixture("tag_wifi", TagModel, "Wi-Fi")
tag_pets = _named_model_fixture("tag_pets", TagModel, "Pet friendly")


# --------------------------------------------------------------------------
# Place factories
# --------------------------------------------------------------------------
@pytest.fixture
def place_payload() -> dict:
    return {
        "name": "Test Place",
        "description": "A place used by endpoint tests.",
        "address": "123 Test Street",
        "opening_hours": {"opens_at": "09:00", "closes_at": "18:00"},
    }


@pytest.fixture
def post_place(client, auth_headers, place_payload):
    """POST /places with the base payload + overrides; returns the Response."""

    async def _post(headers=None, **overrides):
        return await client.post(
            "/places",
            json={**place_payload, **overrides},
            headers=headers or auth_headers,
        )

    return _post


@pytest.fixture
def create_place(post_place):
    """Like post_place, but asserts 201 and returns the JSON body."""

    async def _create(**kwargs):
        return _json_or_fail(await post_place(**kwargs), 201)

    return _create


@pytest.fixture
def create_many_places(create_place, db_session):
    """Factory: create MANY_PLACES_COUNT places, oldest first,
    with explicit created_at.

    created_at is set directly in the DB because
    server-generated timestamps can collide, which
    would make the ordering assertions nondeterministic.
    """

    async def _create_many(name_prefix: str, **overrides) -> list[dict]:
        places = []
        for i in range(MANY_PLACES_COUNT):
            created = await create_place(name=f"{name_prefix} {i}", **overrides)
            await db_session.execute(
                update(PlaceModel)
                .where(PlaceModel.id == UUID(created["id"]))
                .values(created_at=MANY_PLACES_BASE_TIME + timedelta(minutes=i))
            )
            places.append(created)
        await db_session.commit()
        return places

    return _create_many


# --------------------------------------------------------------------------
# Place fixtures
# --------------------------------------------------------------------------
@pytest_asyncio.fixture
async def place(create_place) -> dict:
    return await create_place()


@pytest_asyncio.fixture
async def searchable_places(create_place, place) -> dict[str, str]:
    names = {
        "park": "Central Park",
        "cafe": "Park Side Cafe",
        "museum": "City Museum",
        "discount": "50% Off Shop",
        "underscore": "a_b Bar",
    }
    ids = {"default": place["id"]}
    for key, name in names.items():
        ids[key] = (await create_place(name=name))["id"]
    return ids


@pytest_asyncio.fixture
async def place_cafe(create_place, category_cafe) -> dict:
    return await create_place(
        name="Blue Bottle Coffee", category_ids=_ids([category_cafe])
    )


@pytest_asyncio.fixture
async def place_park(create_place, category_park) -> dict:
    return await create_place(name="Central Park", category_ids=_ids([category_park]))


@pytest_asyncio.fixture
async def place_cafe_and_park(create_place, category_cafe, category_park) -> dict:
    return await create_place(
        name="Park Cafe", category_ids=_ids([category_cafe, category_park])
    )


@pytest_asyncio.fixture
async def many_cafe_places(create_many_places, category_cafe) -> list[dict]:
    """25 cafe places, oldest first, with explicit created_at values."""
    return await create_many_places("Cafe", category_ids=_ids([category_cafe]))


@pytest_asyncio.fixture
async def many_outdoor_places(create_many_places, tag_outdoor) -> list[dict]:
    """25 places with the 'Outdoor' tag, oldest first, explicit created_at."""
    return await create_many_places("Outdoor", tag_ids=_ids([tag_outdoor]))


@pytest_asyncio.fixture
async def tagged_places(
    create_place, tag_outdoor, tag_wifi, tag_pets
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
        key: await create_place(name=name, tag_ids=_ids(tags))
        for key, (name, tags) in specs.items()
    }


@pytest.fixture(params=list(_VIEWS))
def view_place(request, client, auth_headers):
    """Async fn: created place -> the same place as seen via one endpoint.

    `headers` is the viewer (defaults to the owner). Updates are always
    performed by the owner.
    """
    reader = _VIEWS[request.param]

    async def _view(created, headers=None):
        return await reader(client, created, headers or auth_headers, auth_headers)

    return _view
