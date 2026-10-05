import pytest
from app.auth.api_keys import ApiKeyService

@pytest.mark.asyncio
async def test_auth_valid_bearer_key(async_client, test_user_and_key):
    user, api_key, plain_key = test_user_and_key
    headers = {"Authorization": f"Bearer {plain_key}"}
    resp = await async_client.get("/v1/quota", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_limit"] == 5
    assert data["rate_limit_per_minute"] == 1

@pytest.mark.asyncio
async def test_auth_valid_x_api_key(async_client, test_user_and_key):
    user, api_key, plain_key = test_user_and_key
    headers = {"x-api-key": plain_key}
    resp = await async_client.get("/v1/quota", headers=headers)
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_auth_missing_key(async_client):
    resp = await async_client.get("/v1/quota")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] == "authentication_error"

@pytest.mark.asyncio
async def test_auth_invalid_key(async_client):
    headers = {"Authorization": "Bearer nv-invalidnonexistenttoken"}
    resp = await async_client.get("/v1/quota", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["type"] == "authentication_error"

@pytest.mark.asyncio
async def test_auth_revoked_key(async_client, test_db_conn, test_user_and_key):
    user, api_key, plain_key = test_user_and_key
    # Revoke key
    revoked = await ApiKeyService.revoke_key(test_db_conn, api_key.id, user.id)
    assert revoked is True

    headers = {"Authorization": f"Bearer {plain_key}"}
    resp = await async_client.get("/v1/quota", headers=headers)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_api_key_management(async_client, test_user_and_key):
    user, api_key, plain_key = test_user_and_key
    headers = {"Authorization": f"Bearer {plain_key}"}

    # 1. Create a second key
    create_resp = await async_client.post("/v1/api-keys", json={"label": "Second Key"}, headers=headers)
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["key"].startswith("nv-")
    second_key = data["key"]
    second_key_id = data["id"]

    # 2. List keys
    list_resp = await async_client.get("/v1/api-keys", headers=headers)
    assert list_resp.status_code == 200
    keys_list = list_resp.json()
    assert len(keys_list) == 2
    # Verify plaintext key is NOT returned in list
    assert "key" not in keys_list[0]
    assert keys_list[0]["key_prefix"].startswith("nv-")

    # 3. Revoke second key
    del_resp = await async_client.delete(f"/v1/api-keys/{second_key_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["revoked"] is True

    # 4. Using revoked second key should fail
    fail_resp = await async_client.get("/v1/quota", headers={"Authorization": f"Bearer {second_key}"})
    assert fail_resp.status_code == 401
