async def test_list_places_returns_created_place(client, place):
    response = await client.get("/places")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == place["id"]


async def test_list_places_filters_by_search(client, place):
    response = await client.get("/places", params={"search": "Test Place"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [place["id"]]


async def test_list_places_rejects_invalid_pagination(client):
    response = await client.get("/places", params={"page": 0})

    assert response.status_code == 422
