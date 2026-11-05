import pytest

pytestmark = pytest.mark.asyncio

HOURS = {"opens_at": "09:00", "closes_at": "18:00"}
NEW_HOURS = {"opens_at": "08:30", "closes_at": "20:15"}


# --- valid values: every endpoint returns the same normalized shape ---------
@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        (HOURS, HOURS),
        (
            {"opens_at": "00:00", "closes_at": "23:59"},
            {"opens_at": "00:00", "closes_at": "23:59"},
        ),
        # seconds are accepted on input but serialized as HH:MM
        (
            {"opens_at": "09:30:45", "closes_at": "18:15:10"},
            {"opens_at": "09:30", "closes_at": "18:15"},
        ),
        (None, None),
    ],
    ids=["typical", "full-day", "seconds-dropped", "null"],
)
async def test_opening_hours_are_returned_normalized(
    create_place, view_place, sent, expected
):
    created = await create_place(opening_hours=sent)

    shown = await view_place(created)

    assert shown["opening_hours"] == expected


async def test_opening_hours_default_to_null_when_omitted(
    client, auth_headers, place_payload
):
    payload = {k: v for k, v in place_payload.items() if k != "opening_hours"}

    response = await client.post("/places", json=payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    assert response.json()["opening_hours"] is None


# --- invalid values are rejected on create and on update --------------------
INVALID_HOURS = [
    pytest.param({"opens_at": "18:00", "closes_at": "09:00"}, id="opens-after-closes"),
    pytest.param({"opens_at": "09:00", "closes_at": "09:00"}, id="opens-equals-closes"),
    pytest.param({"opens_at": "09:00"}, id="missing-closes_at"),
    pytest.param({"closes_at": "18:00"}, id="missing-opens_at"),
    pytest.param({"opens_at": "9am", "closes_at": "6pm"}, id="bad-format"),
    pytest.param({"opens_at": "25:00", "closes_at": "26:00"}, id="out-of-range"),
    pytest.param("09:00-18:00", id="string-instead-of-object"),
]


@pytest.mark.parametrize("invalid", INVALID_HOURS)
async def test_create_rejects_invalid_opening_hours(post_place, invalid):
    response = await post_place(opening_hours=invalid)

    assert response.status_code == 422


@pytest.mark.parametrize("invalid", INVALID_HOURS)
async def test_update_rejects_invalid_opening_hours_and_keeps_old_value(
    client, auth_headers, create_place, invalid
):
    created = await create_place(opening_hours=HOURS)
    url = f"/places/{created['id']}"

    response = await client.patch(
        url, json={"opening_hours": invalid}, headers=auth_headers
    )
    assert response.status_code == 422

    unchanged = await client.get(url, headers=auth_headers)
    assert unchanged.json()["opening_hours"] == HOURS


# --- update semantics --------------------------------------------------------
@pytest.mark.parametrize(
    ("sent", "expected"),
    [(NEW_HOURS, NEW_HOURS), (None, None)],
    ids=["change", "clear-with-null"],
)
async def test_update_opening_hours(client, auth_headers, create_place, sent, expected):
    created = await create_place(opening_hours=HOURS)
    url = f"/places/{created['id']}"

    response = await client.patch(
        url, json={"opening_hours": sent}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["opening_hours"] == expected

    persisted = await client.get(url, headers=auth_headers)
    assert persisted.json()["opening_hours"] == expected
