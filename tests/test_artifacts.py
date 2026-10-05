import pytest
from app.artifacts.service import ArtifactService
from app.artifacts.storage import artifact_storage, validate_safe_filename
from app.core.errors import InvalidRequestError, ArtifactNotFoundError

def test_path_traversal_prevention():
    # Traversal characters
    with pytest.raises(InvalidRequestError):
        validate_safe_filename("../../../etc/passwd")

    with pytest.raises(InvalidRequestError):
        validate_safe_filename("..\\..\\windows\\system32")

    # Windows drive paths
    with pytest.raises(InvalidRequestError):
        validate_safe_filename("C:\\autoexec.bat")

    # Null bytes
    with pytest.raises(InvalidRequestError):
        validate_safe_filename("file.txt\0.jpg")

@pytest.mark.asyncio
async def test_artifact_lifecycle_and_ownership(async_client, test_db_conn, test_user_and_key):
    user1, key1, plain_key1 = test_user_and_key

    # 1. Create artifact for user 1
    art_record = await ArtifactService.create_artifact(
        db=test_db_conn,
        user_id=user1.id,
        task_id="task_123",
        filename="summary.md",
        content="# Test Markdown Summary\nCreated by agent.",
    )
    assert art_record.id.startswith("art_")
    assert art_record.filename == "summary.md"

    # 2. User 1 can download it
    headers1 = {"Authorization": f"Bearer {plain_key1}"}
    resp1 = await async_client.get(f"/v1/artifacts/{art_record.id}", headers=headers1)
    assert resp1.status_code == 200
    assert "# Test Markdown Summary" in resp1.text

    # 3. Create user 2
    from app.db.repositories import UserRepository
    from app.auth.api_keys import ApiKeyService
    user2 = await UserRepository.create_user(test_db_conn, "usr_user2", "user2")
    plain_key2, _ = await ApiKeyService.create_key_for_user(test_db_conn, user2.id)
    headers2 = {"Authorization": f"Bearer {plain_key2}"}

    # 4. User 2 trying to read User 1's artifact is blocked
    resp2 = await async_client.get(f"/v1/artifacts/{art_record.id}", headers=headers2)
    assert resp2.status_code == 404
