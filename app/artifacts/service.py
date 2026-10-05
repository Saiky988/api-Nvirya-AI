import mimetypes
from typing import Optional
import aiosqlite
from app.artifacts.storage import artifact_storage
from app.core.errors import ArtifactNotFoundError
from app.db.models import ArtifactRecord
from app.db.repositories import ArtifactRepository

class ArtifactService:
    @staticmethod
    async def create_artifact(
        db: aiosqlite.Connection,
        user_id: str,
        task_id: str,
        filename: str,
        content: str,
    ) -> ArtifactRecord:
        artifact_id, file_path, file_size = artifact_storage.save_persistent_artifact(
            user_id=user_id,
            task_id=task_id,
            filename=filename,
            content=content,
        )
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "text/plain"

        return await ArtifactRepository.create_artifact(
            db=db,
            artifact_id=artifact_id,
            user_id=user_id,
            task_id=task_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
        )

    @staticmethod
    async def get_artifact(
        db: aiosqlite.Connection,
        artifact_id: str,
        user_id: str,
    ) -> tuple[ArtifactRecord, bytes]:
        record = await ArtifactRepository.get_artifact(db, artifact_id, user_id=user_id)
        if not record:
            raise ArtifactNotFoundError("Artifact not found or access denied.")

        file_bytes = artifact_storage.read_persistent_artifact(record.file_path)
        return record, file_bytes
