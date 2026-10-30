async def test_get_place_returns_detail(client, place):
    response = await client.get(f"/places/{place['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == place["id"]
    assert response.json()["name"] == place["name"]


async def test_get_missing_place_returns_404(client):
    response = await client.get("/places/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


async def test_get_place_rejects_invalid_id(client):
    response = await client.get("/places/not-a-uuid")

    assert response.status_code == 422
