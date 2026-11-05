import pytest
import pytest_asyncio
from uuid import uuid4

pytestmark = pytest.mark.asyncio

OTHER_USER = {
    "display_name": "Other User",
    "email": "other@example.com",
    "password": "StrongPass123!",
}


@pytest_asyncio.fixture
async def other_user_headers(client) -> dict:
    """Auth headers for a second, independent user."""
    registered = await client.post("/auth/register", json=OTHER_USER)
    assert registered.status_code == 201, registered.text
    login = await client.post(
        "/auth/login",
        json={"email": OTHER_USER["email"], "password": OTHER_USER["password"]},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_creator_name_is_the_creators_display_name(
    create_place, view_place, register_payload
):
    created = await create_place()

    shown = await view_place(created)

    assert shown["creator_name"] == register_payload["display_name"]


async def test_creator_name_is_not_the_viewers_name(
    create_place, view_place, other_user_headers, register_payload
):
    created = await create_place()

    shown = await view_place(created, headers=other_user_headers)

    assert shown["creator_name"] == register_payload["display_name"]


async def test_each_place_reports_its_own_creator(
    client, auth_headers, other_user_headers, create_place, register_payload
):
    mine = await create_place(name="Mine")
    theirs = await create_place(headers=other_user_headers, name="Theirs")

    response = await client.get("/places", headers=auth_headers)
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    names = {item["id"]: item["creator_name"] for item in items}

    assert names[mine["id"]] == register_payload["display_name"]
    assert names[theirs["id"]] == OTHER_USER["display_name"]


async def test_creator_name_cannot_be_set_by_the_client(create_place, register_payload):
    created = await create_place(creator_name="Mallory", creator_id=str(uuid4()))

    assert created["creator_name"] == register_payload["display_name"]
