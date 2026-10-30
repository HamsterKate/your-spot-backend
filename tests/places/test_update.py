async def test_update_place_changes_provided_fields(client, auth_headers, place):
    response = await client.patch(
        f"/places/{place['id']}",
        json={"name": "Updated Place"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Place"


async def test_update_place_requires_authentication(client, place):
    response = await client.patch(
        f"/places/{place['id']}", json={"name": "Updated Place"}
    )

    assert response.status_code in (401, 403)


async def test_update_place_rejects_unknown_fields(client, auth_headers, place):
    response = await client.patch(
        f"/places/{place['id']}",
        json={"creator_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth_headers,
    )

    assert response.status_code == 422
