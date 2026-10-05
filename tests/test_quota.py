import pytest
from app.auth.api_keys import ApiKeyService
from app.quotas.daily import DailyQuotaService, get_current_date_vn
from app.quotas.rate_limit import rate_limiter

@pytest.mark.asyncio
async def test_rate_limiter_sliding_window():
    limiter = rate_limiter
    limiter.clear()
    key = "test_key_1"

    # 1. First request allowed
    await limiter.check_and_record(key)

    # 2. Second request immediately blocked
    with pytest.raises(Exception) as excinfo:
        await limiter.check_and_record(key)
    assert "rate limit exceeded" in str(excinfo.value).lower()

    # 3. Reset works
    limiter.reset_key(key)
    await limiter.check_and_record(key)  # Allowed again

@pytest.mark.asyncio
async def test_daily_quota_consumption(test_db_conn):
    user_id = "usr_quota_test"
    today = get_current_date_vn()

    # Consume up to limit (5)
    for _ in range(5):
        await DailyQuotaService.consume_quota(test_db_conn, user_id)

    info = await DailyQuotaService.get_user_quota_info(test_db_conn, user_id)
    assert info[1] == 5  # daily_used
    assert info[2] == 0  # daily_remaining

    # 6th request fails with QuotaExceededError
    with pytest.raises(Exception) as excinfo:
        await DailyQuotaService.consume_quota(test_db_conn, user_id)
    assert "daily task quota" in str(excinfo.value).lower()

@pytest.mark.asyncio
async def test_user_level_quota_shared_across_keys(async_client, test_db_conn, test_user_and_key):
    user, key1, plain_key1 = test_user_and_key
    # Create second key for same user
    plain_key2, key2 = await ApiKeyService.create_key_for_user(test_db_conn, user.id, label="Key 2")

    headers1 = {"Authorization": f"Bearer {plain_key1}"}
    headers2 = {"Authorization": f"Bearer {plain_key2}"}

    # Consume quota using key1
    for _ in range(5):
        await DailyQuotaService.consume_quota(test_db_conn, user.id)

    # Both keys must now see 0 quota remaining
    resp1 = await async_client.get("/v1/quota", headers=headers1)
    assert resp1.status_code == 200
    assert resp1.json()["daily_remaining"] == 0

    resp2 = await async_client.get("/v1/quota", headers=headers2)
    assert resp2.status_code == 200
    assert resp2.json()["daily_remaining"] == 0
