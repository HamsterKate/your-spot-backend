async def test_create_place_returns_detail_and_location_header(
    client, auth_headers, place_payload
):
    response = await client.post("/places", json=place_payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == place_payload["name"]
    assert data["opening_hours"] is None


async def test_create_place_requires_authentication(client, place_payload):
    response = await client.post("/places", json=place_payload)

    assert response.status_code in (401, 403)


async def test_create_place_requires_address_or_coordinates(
    client, auth_headers, place_payload
):
    place_payload.pop("address")

    response = await client.post("/places", json=place_payload, headers=auth_headers)

    assert response.status_code == 422
