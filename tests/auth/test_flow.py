async def test_full_auth_flow(client, register_payload):
    # register
    reg = await client.post("/auth/register", json=register_payload)
    assert reg.status_code == 201

    # login
    login = await client.post(
        "/auth/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"],
        },
    )
    assert login.status_code == 200
    first = login.json()

    # refresh
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert refreshed.status_code == 200
    second = refreshed.json()

    # logout with the newest access token
    logout = await client.get(
        "/auth/logout", headers={"Authorization": f"Bearer {second['access_token']}"}
    )
    assert logout.status_code == 204
