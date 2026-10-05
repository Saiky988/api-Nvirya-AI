import asyncio
import pytest
from app.tasks.service import TaskService

@pytest.mark.asyncio
async def test_task_lifecycle_api(async_client, test_db_conn, test_user_and_key):
    user, key, plain_key = test_user_and_key
    headers = {"Authorization": f"Bearer {plain_key}"}

    # 1. Create task
    payload = {
        "model": "nvirya-auto",
        "messages": [{"role": "user", "content": "Sample task instruction"}],
    }
    resp = await async_client.post("/v1/tasks", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "task"
    assert data["status"] in ("created", "running")
    task_id = data["id"]

    # 2. Get task status
    get_resp = await async_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id

    # 3. Cancel task
    cancel_resp = await async_client.post(f"/v1/tasks/{task_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # 4. Verify status is now cancelled
    after_cancel = await async_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert after_cancel.json()["status"] == "cancelled"
