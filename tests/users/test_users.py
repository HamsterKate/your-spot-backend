from uuid import UUID

import pytest

from app.core.config import settings
from app.users.models import UserModel
from tests.conftest import GIF, JPEG, PNG, WEBP, get_me, avatar_file, avatar_path

pytestmark = pytest.mark.asyncio

OTHER_EMAIL = "other@example.com"
NO_ACCESS = (401, 403)


# --------------------------------------------------------------------------
# GET /users/me
# --------------------------------------------------------------------------
async def test_get_me_returns_current_user(client, auth_headers, register_payload):
    body = await get_me(client, auth_headers)

    assert body["display_name"] == register_payload["display_name"]
    assert body["email"] == register_payload["email"]
    assert UUID(body["id"])
    assert body["avatar_url"] is None


async def test_get_me_does_not_leak_sensitive_fields(client, auth_headers):
    body = await get_me(client, auth_headers)

    assert "password" not in body
    assert "password_hash" not in body


async def test_get_me_requires_authentication(client):
    response = await client.get("/users/me")

    assert response.status_code in NO_ACCESS


async def test_get_me_rejects_invalid_token(client):
    response = await client.get(
        "/users/me", headers={"Authorization": "Bearer not-a-token"}
    )

    assert response.status_code in NO_ACCESS


# --------------------------------------------------------------------------
# PATCH /users/me: authentication and general behavior
# --------------------------------------------------------------------------
async def test_update_me_requires_authentication(client):
    response = await client.patch("/users/me", data={"display_name": "X"})

    assert response.status_code in NO_ACCESS


async def test_update_me_empty_request_changes_nothing(client, auth_headers, patch_me):
    before = await get_me(client, auth_headers)

    response = await patch_me()

    assert response.status_code == 200, response.text
    assert response.json() == before


async def test_update_me_all_fields_at_once(client, auth_headers, patch_me, storage):
    response = await patch_me(
        data={"display_name": "New Name", "email": "new@example.com"},
        files=avatar_file(PNG, "image/png", "a.png"),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "New Name"
    assert body["email"] == "new@example.com"
    assert body["avatar_url"] is not None
    assert await get_me(client, auth_headers) == body
    assert len(storage.objects) == 1


# --------------------------------------------------------------------------
# PATCH /users/me: display_name
# --------------------------------------------------------------------------
async def test_update_display_name_persists(client, auth_headers, patch_me):
    response = await patch_me(data={"display_name": "Renamed"})

    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Renamed"
    assert (await get_me(client, auth_headers))["display_name"] == "Renamed"


async def test_update_display_name_does_not_touch_email(
    client, auth_headers, patch_me, register_payload
):
    await patch_me(data={"display_name": "Renamed"})

    body = await get_me(client, auth_headers)
    assert body["email"] == register_payload["email"]


async def test_update_display_name_strips_whitespace(patch_me):
    response = await patch_me(data={"display_name": "   Padded   "})

    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Padded"


async def test_update_display_name_accepts_max_length(patch_me):
    name = "a" * 50

    response = await patch_me(data={"display_name": name})

    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == name


@pytest.mark.parametrize("value", ["   ", "a" * 51])
async def test_update_display_name_rejects_invalid_values(
    client, auth_headers, patch_me, register_payload, value
):
    response = await patch_me(data={"display_name": value})

    assert response.status_code == 422
    body = await get_me(client, auth_headers)
    assert body["display_name"] == register_payload["display_name"]


# --------------------------------------------------------------------------
# PATCH /users/me: email
# --------------------------------------------------------------------------
async def test_update_email_persists(client, auth_headers, patch_me):
    response = await patch_me(data={"email": "new@example.com"})

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "new@example.com"
    assert (await get_me(client, auth_headers))["email"] == "new@example.com"


async def test_update_email_is_lowercased(patch_me):
    response = await patch_me(data={"email": "MiXeD@Example.COM"})

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "mixed@example.com"


async def test_update_email_allows_login_with_new_email(
    client, patch_me, register_payload
):
    await patch_me(data={"email": "new@example.com"})

    response = await client.post(
        "/auth/login",
        json={"email": "new@example.com", "password": register_payload["password"]},
    )

    assert response.status_code == 200, response.text


async def test_update_email_resubmitting_own_email_is_ok(patch_me, register_payload):
    response = await patch_me(data={"email": register_payload["email"]})

    assert response.status_code == 200, response.text


async def test_update_email_own_email_in_different_case_is_ok(
    patch_me, register_payload
):
    response = await patch_me(data={"email": register_payload["email"].upper()})

    assert response.status_code == 200, response.text
    assert response.json()["email"] == register_payload["email"].lower()


@pytest.mark.parametrize(
    "value",
    [
        "not-an-email",
        "a@",
        "@example.com",
    ],
)
async def test_update_email_rejects_invalid_email(
    client, auth_headers, patch_me, register_payload, value
):
    response = await patch_me(data={"email": value})

    assert response.status_code == 422
    body = await get_me(client, auth_headers)
    assert body["email"] == register_payload["email"]


async def test_update_email_rejects_email_used_by_another_user(
    client, auth_headers, patch_me, make_auth_headers, register_payload
):
    await make_auth_headers("Other", OTHER_EMAIL)

    response = await patch_me(data={"email": OTHER_EMAIL})

    assert response.status_code == 409
    body = await get_me(client, auth_headers)
    assert body["email"] == register_payload["email"]


async def test_update_email_conflict_is_case_insensitive(patch_me, make_auth_headers):
    await make_auth_headers("Other", OTHER_EMAIL)

    response = await patch_me(data={"email": OTHER_EMAIL.upper()})

    assert response.status_code == 409


async def test_update_email_conflict_does_not_apply_display_name(
    client, auth_headers, patch_me, make_auth_headers, register_payload
):
    await make_auth_headers("Other", OTHER_EMAIL)

    response = await patch_me(
        data={"display_name": "Should Not Apply", "email": OTHER_EMAIL}
    )

    assert response.status_code == 409
    body = await get_me(client, auth_headers)
    assert body["display_name"] == register_payload["display_name"]


async def test_update_email_unique_constraint_race_returns_409_and_cleans_up(
    monkeypatch, patch_me, make_auth_headers, storage
):
    # Simulate two concurrent requests: the pre-check passes, the DB rejects
    await make_auth_headers("Other", OTHER_EMAIL)

    async def never_taken(*args, **kwargs):
        return False

    monkeypatch.setattr("app.users.services._email_taken", never_taken)

    response = await patch_me(data={"email": OTHER_EMAIL}, files=avatar_file(JPEG))

    assert response.status_code == 409
    assert storage.objects == {}


# --------------------------------------------------------------------------
# PATCH /users/me: avatar upload
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("content", "content_type"),
    [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")],
    ids=["jpeg", "png", "webp"],
)
async def test_upload_avatar_accepts_supported_formats(
    patch_me, storage, db_session, content, content_type
):
    response = await patch_me(files=avatar_file(content, content_type))

    assert response.status_code == 200, response.text
    body = response.json()

    user = await db_session.get(UserModel, UUID(body["id"]))
    key = f"users/avatars/{user.avatar_object_id}"
    assert body["avatar_url"].endswith(f"/users/avatars/{user.avatar_object_id}")
    assert user.avatar_content_type == content_type
    assert storage.objects == {key: (content, content_type)}


async def test_upload_avatar_url_appears_in_get_me(client, auth_headers, upload_avatar):
    uploaded = await upload_avatar()

    body = await get_me(client, auth_headers)
    assert body["avatar_url"] == uploaded["avatar_url"]


async def test_upload_avatar_only_keeps_profile_fields(patch_me, register_payload):
    response = await patch_me(files=avatar_file())

    body = response.json()
    assert body["display_name"] == register_payload["display_name"]
    assert body["email"] == register_payload["email"]


async def test_upload_avatar_declared_content_type_is_ignored(
    patch_me, storage, db_session
):
    # PNG bytes labelled as JPEG: the stored type follows the real signature
    response = await patch_me(files=avatar_file(PNG, "image/jpeg", "x.jpg"))

    assert response.status_code == 200, response.text
    user = await db_session.get(UserModel, UUID(response.json()["id"]))
    assert user.avatar_content_type == "image/png"
    assert next(iter(storage.objects.values()))[1] == "image/png"


async def test_upload_avatar_filename_is_not_used_in_object_key(patch_me, storage):
    await patch_me(files=avatar_file(JPEG, "image/jpeg", "../../evil.jpg"))

    assert storage.objects
    assert all(
        key.startswith("users/avatars/") and "evil" not in key
        for key in storage.objects
    )


async def test_upload_avatar_accepts_file_at_exact_size_limit(patch_me, storage):
    content = JPEG + b"0" * (settings.max_photo_size_bytes - len(JPEG))

    response = await patch_me(files=avatar_file(content))

    assert response.status_code == 200, response.text
    assert len(storage.objects) == 1


# --------------------------------------------------------------------------
# PATCH /users/me: avatar validation
# --------------------------------------------------------------------------
async def test_avatar_validation_rejects_empty_file(patch_me, storage):
    response = await patch_me(files=avatar_file(b""))

    assert response.status_code == 400
    assert storage.objects == {}


async def test_avatar_validation_rejects_oversized_file(patch_me, storage):
    content = JPEG + b"0" * settings.max_photo_size_bytes

    response = await patch_me(files=avatar_file(content))

    assert response.status_code == 413
    assert storage.objects == {}


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (GIF, "image/gif"),
        (b"<script>alert(1)</script>", "image/png"),
        (b"plain text, not an image", "image/jpeg"),
        (b"%PDF-1.7 " + b"0" * 32, "application/pdf"),
        (b"RIFF\x00\x00\x00\x00WAVE" + b"0" * 32, "image/webp"),
    ],
    ids=["gif", "html-as-png", "text-as-jpeg", "pdf", "riff-but-not-webp"],
)
async def test_avatar_validation_rejects_unsupported_or_spoofed_content(
    patch_me, storage, content, content_type
):
    response = await patch_me(files=avatar_file(content, content_type))

    assert response.status_code == 400
    assert storage.objects == {}


async def test_avatar_validation_failure_blocks_whole_update(
    client, auth_headers, patch_me, register_payload
):
    response = await patch_me(
        data={"display_name": "Should Not Apply", "email": "new@example.com"},
        files=avatar_file(GIF, "image/gif"),
    )

    assert response.status_code == 400
    body = await get_me(client, auth_headers)
    assert body["display_name"] == register_payload["display_name"]
    assert body["email"] == register_payload["email"]


async def test_avatar_validation_failure_keeps_existing_avatar(
    patch_me, upload_avatar, storage
):
    await upload_avatar(PNG, "image/png")
    snapshot = dict(storage.objects)

    response = await patch_me(files=avatar_file(GIF, "image/gif"))

    assert response.status_code == 400
    assert storage.objects == snapshot


# --------------------------------------------------------------------------
# PATCH /users/me: replacing an avatar
# --------------------------------------------------------------------------
async def test_replace_avatar_uses_new_object_id_and_deletes_old_object(
    upload_avatar, storage, db_session
):
    first = await upload_avatar(JPEG, "image/jpeg")
    user = await db_session.get(UserModel, UUID(first["id"]))
    old_id = user.avatar_object_id

    await upload_avatar(PNG, "image/png")

    assert user.avatar_object_id != old_id
    assert user.avatar_content_type == "image/png"
    assert f"users/avatars/{old_id}" not in storage.objects
    assert list(storage.objects) == [f"users/avatars/{user.avatar_object_id}"]


async def test_replace_avatar_serves_the_new_one(client, upload_avatar):
    await upload_avatar(JPEG, "image/jpeg")
    second = await upload_avatar(PNG, "image/png")

    response = await client.get(avatar_path(second))

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"


async def test_replace_avatar_old_object_cleanup_failure_does_not_fail_request(
    client, upload_avatar, patch_me, storage
):
    first = await upload_avatar(JPEG, "image/jpeg")
    storage.fail_delete = True

    response = await patch_me(files=avatar_file(PNG, "image/png"))

    assert response.status_code == 200, response.text
    assert len(storage.objects) == 2  # old one orphaned, harmless
    assert (await client.get(avatar_path(response.json()))).content == PNG
    assert (await client.get(avatar_path(first))).status_code == 404


async def test_replace_avatar_storage_failure_keeps_old_avatar_and_profile(
    client, auth_headers, upload_avatar, patch_me, storage, register_payload
):
    first = await upload_avatar(JPEG, "image/jpeg")
    snapshot = dict(storage.objects)
    storage.fail_upload = True

    response = await patch_me(
        data={"display_name": "Should Not Apply"},
        files=avatar_file(PNG, "image/png"),
    )

    assert response.status_code == 502
    assert storage.objects == snapshot
    storage.fail_upload = False
    body = await get_me(client, auth_headers)
    assert body["display_name"] == register_payload["display_name"]
    served = await client.get(avatar_path(first))
    assert served.content == JPEG


async def test_replace_avatar_db_commit_failure_removes_new_object_keeps_old(
    monkeypatch, db_session, upload_avatar, patch_me, storage
):
    await upload_avatar(JPEG, "image/jpeg")
    snapshot = dict(storage.objects)

    async def broken_commit():
        raise RuntimeError("db down")

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(RuntimeError, match="db down"):
        await patch_me(files=avatar_file(PNG, "image/png"))

    assert storage.objects == snapshot


async def test_replace_avatar_changes_avatar_url(upload_avatar):
    first = await upload_avatar(JPEG, "image/jpeg")
    second = await upload_avatar(PNG, "image/png")

    assert first["avatar_url"] != second["avatar_url"]


async def test_replace_avatar_old_url_returns_404(client, upload_avatar):
    first = await upload_avatar(JPEG, "image/jpeg")
    await upload_avatar(PNG, "image/png")

    response = await client.get(avatar_path(first))

    assert response.status_code == 404


# --------------------------------------------------------------------------
# PATCH /users/me: storage failure on first upload
# --------------------------------------------------------------------------
async def test_first_upload_storage_failure_returns_502_and_leaves_no_avatar(
    client, auth_headers, patch_me, storage
):
    storage.fail_upload = True

    response = await patch_me(files=avatar_file())

    assert response.status_code == 502
    assert (await get_me(client, auth_headers))["avatar_url"] is None


# --------------------------------------------------------------------------
# GET /users/avatar/{avatar_id}
# --------------------------------------------------------------------------
async def test_get_avatar_returns_bytes_and_headers(client, upload_avatar):
    body = await upload_avatar(WEBP, "image/webp")

    response = await client.get(avatar_path(body))

    assert response.status_code == 200
    assert response.content == WEBP
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_get_avatar_is_cacheable_forever(client, upload_avatar):
    body = await upload_avatar()

    response = await client.get(avatar_path(body))

    cache_control = response.headers["cache-control"]
    assert "max-age=31536000" in cache_control
    assert "immutable" in cache_control


async def test_get_avatar_is_public(client, upload_avatar):
    body = await upload_avatar()

    response = await client.get(avatar_path(body))  # no Authorization header

    assert response.status_code == 200


async def test_get_avatar_is_viewable_by_other_users(
    client, upload_avatar, make_auth_headers
):
    body = await upload_avatar()
    other = await make_auth_headers("Other", OTHER_EMAIL)

    response = await client.get(avatar_path(body), headers=other)

    assert response.status_code == 200
    assert response.content == JPEG


async def test_get_avatar_404_for_unknown_avatar_id(client):
    response = await client.get("/users/avatars/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404


async def test_get_avatar_422_for_malformed_avatar_id(client):
    response = await client.get("/users/avatars/not-a-uuid")

    assert response.status_code == 422


async def test_get_avatar_502_when_storage_unavailable(client, upload_avatar, storage):
    body = await upload_avatar()
    storage.fail_get = True

    response = await client.get(avatar_path(body))

    assert response.status_code == 502


async def test_get_avatar_users_have_separate_avatars(
    client, upload_avatar, make_auth_headers, storage
):
    mine = await upload_avatar(JPEG, "image/jpeg")
    other_headers = await make_auth_headers("Other", OTHER_EMAIL)
    other = await client.patch(
        "/users/me", files=avatar_file(PNG, "image/png"), headers=other_headers
    )
    assert other.status_code == 200, other.text

    assert (await client.get(avatar_path(mine))).content == JPEG
    assert (await client.get(avatar_path(other.json()))).content == PNG
    assert len(storage.objects) == 2
