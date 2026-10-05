import os
from pathlib import Path
import shutil
import uuid
from typing import Optional
from app.core.config import settings
from app.core.errors import InvalidRequestError, ArtifactNotFoundError

def validate_safe_filename(name: str) -> str:
    """Ensures filename has no directory traversal, drive letters, or null bytes."""
    if not name or not isinstance(name, str):
        raise InvalidRequestError("Filename must be a non-empty string.")

    cleaned = name.replace("\\", "/").strip()
    if "\0" in cleaned or ":" in cleaned:
        raise InvalidRequestError("Filename contains invalid characters.")

    parts = cleaned.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise InvalidRequestError("Directory traversal characters are not permitted.")

    # Return pure basename or clean relative subpath
    pure_name = parts[-1]
    return pure_name

class ArtifactStorage:
    def __init__(self):
        self.artifacts_root = settings.ARTIFACTS_DIR
        self.temp_root = settings.TEMP_DIR

    def get_task_workspace(self, task_id: str) -> Path:
        safe_task_id = validate_safe_filename(task_id)
        workspace = self.temp_root / safe_task_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def cleanup_workspace(self, task_id: str) -> None:
        safe_task_id = validate_safe_filename(task_id)
        workspace = self.temp_root / safe_task_id
        if workspace.exists() and workspace.is_dir():
            shutil.rmtree(workspace, ignore_errors=True)

    def write_workspace_file(self, task_id: str, filename: str, content: str) -> tuple[Path, int]:
        safe_name = validate_safe_filename(filename)
        workspace = self.get_task_workspace(task_id)
        target = (workspace / safe_name).resolve()

        # Boundary check
        if not str(target).startswith(str(workspace.resolve())):
            raise InvalidRequestError("Path escapes task workspace.")

        data = content.encode("utf-8")
        max_bytes = settings.MAX_ARTIFACT_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise InvalidRequestError(f"File size exceeds maximum allowed ({settings.MAX_ARTIFACT_MB} MB).")

        target.write_bytes(data)
        return target, len(data)

    def read_workspace_file(self, task_id: str, filename: str) -> str:
        safe_name = validate_safe_filename(filename)
        workspace = self.get_task_workspace(task_id)
        target = (workspace / safe_name).resolve()

        if not str(target).startswith(str(workspace.resolve())):
            raise InvalidRequestError("Path escapes task workspace.")

        if not target.exists() or not target.is_file():
            raise ArtifactNotFoundError(f"File '{filename}' does not exist in task workspace.")

        return target.read_text(encoding="utf-8", errors="replace")

    def save_persistent_artifact(
        self,
        user_id: str,
        task_id: str,
        filename: str,
        content: str,
    ) -> tuple[str, str, int]:
        """
        Saves an artifact into persistent storage: storage/artifacts/{user_id}/{task_id}/{artifact_id}_{filename}
        Returns: (artifact_id, relative_path, file_size)
        """
        safe_user = validate_safe_filename(user_id)
        safe_task = validate_safe_filename(task_id)
        safe_filename = validate_safe_filename(filename)

        artifact_id = f"art_{uuid.uuid4().hex[:16]}"
        target_dir = self.artifacts_root / safe_user / safe_task
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / f"{artifact_id}_{safe_filename}"
        data = content.encode("utf-8")

        max_bytes = settings.MAX_ARTIFACT_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise InvalidRequestError(f"Artifact size exceeds maximum allowed ({settings.MAX_ARTIFACT_MB} MB).")

        target_file.write_bytes(data)
        rel_path = str(target_file.relative_to(settings.BASE_DIR))
        return artifact_id, rel_path, len(data)

    def read_persistent_artifact(self, file_path: str) -> bytes:
        target = (settings.BASE_DIR / file_path).resolve()
        artifacts_root_resolved = self.artifacts_root.resolve()
        if not str(target).startswith(str(artifacts_root_resolved)):
            raise InvalidRequestError("Security boundary violation.")

        if not target.exists() or not target.is_file():
            raise ArtifactNotFoundError("Artifact file not found.")

        return target.read_bytes()

artifact_storage = ArtifactStorage()
