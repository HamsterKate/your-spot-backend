async def test_full_places_flow(client, auth_headers, place_payload):
    initial_list = await client.get("/places")
    assert initial_list.status_code == 200
    assert len(initial_list.json()) == 0

    created = await client.post("/places", json=place_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    place = created.json()
    place_id = place["id"]
    assert created.headers["location"] == place["url"]

    mine = await client.get("/places/me", headers=auth_headers)
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()] == [place_id]

    fetched = await client.get(f"/places/{place_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == place_payload["name"]

    updated = await client.patch(
        f"/places/{place_id}",
        json={"name": "Updated Place"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Place"

    after_update = await client.get("/places", params={"search": "Updated"})
    assert after_update.status_code == 200
    assert [item["id"] for item in after_update.json()] == [place_id]

    deleted = await client.delete(f"/places/{place_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/places/{place_id}")).status_code == 404
