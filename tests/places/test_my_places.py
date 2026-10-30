async def test_list_my_places_returns_current_users_places(client, auth_headers, place):
    response = await client.get("/places/me", headers=auth_headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [place["id"]]
