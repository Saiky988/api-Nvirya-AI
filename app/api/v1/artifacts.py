import aiosqlite
from fastapi import APIRouter, Depends, Response
from app.artifacts.service import ArtifactService
from app.auth.dependencies import AuthContext, get_current_auth
from app.db.database import get_db

router = APIRouter()

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    auth: AuthContext = Depends(get_current_auth),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Downloads or views an artifact belonging to the authenticated user."""
    record, file_bytes = await ArtifactService.get_artifact(
        db=db,
        artifact_id=artifact_id,
        user_id=auth.user.id,
    )

    headers = {
        "Content-Disposition": f'inline; filename="{record.filename}"',
        "Content-Length": str(record.file_size),
    }

    return Response(
        content=file_bytes,
        media_type=record.mime_type or "text/plain",
        headers=headers,
    )
