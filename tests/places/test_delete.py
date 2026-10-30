async def test_delete_place_removes_it(client, auth_headers, place):
    response = await client.delete(f"/places/{place['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(f"/places/{place['id']}")).status_code == 404


async def test_delete_place_requires_authentication(client, place):
    response = await client.delete(f"/places/{place['id']}")

    assert response.status_code in (401, 403)
