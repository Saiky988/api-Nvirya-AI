from typing import Any
from app.artifacts.service import ArtifactService
from app.artifacts.storage import artifact_storage
from app.tools.base import BaseTool, ToolContext

class FileCreateTool(BaseTool):
    name = "file_create"
    description = "Create a file or artifact in the task workspace. Use this when the user requests generating documents, reports, code files, or markdown summaries."
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Name of the file to create (e.g. 'summary.md', 'output.json'). Path traversal characters are forbidden.",
            },
            "content": {
                "type": "string",
                "description": "Text content to write to the file.",
            },
        },
        "required": ["filename", "content"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        filename = arguments.get("filename", "").strip()
        content = arguments.get("content", "")
        if not filename:
            return "Error: 'filename' parameter is required."

        try:
            # 1. Write to workspace
            path, size = artifact_storage.write_workspace_file(
                task_id=context.task_id, filename=filename, content=content
            )

            # 2. If DB available, also register persistent artifact
            artifact_info = ""
            if context.db:
                record = await ArtifactService.create_artifact(
                    db=context.db,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    filename=filename,
                    content=content,
                )
                artifact_info = f" (Artifact ID: {record.id})"

            return f"Successfully created file '{filename}' ({size} bytes){artifact_info}."
        except Exception as e:
            return f"Error creating file '{filename}': {str(e)}"


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Read the contents of a file previously created in this task's workspace."
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Name of the file to read from the task workspace.",
            }
        },
        "required": ["filename"],
    }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> str:
        filename = arguments.get("filename", "").strip()
        if not filename:
            return "Error: 'filename' parameter is required."

        try:
            content = artifact_storage.read_workspace_file(
                task_id=context.task_id, filename=filename
            )
            return f"Contents of '{filename}':\n\n{content}"
        except Exception as e:
            return f"Error reading file '{filename}': {str(e)}"
