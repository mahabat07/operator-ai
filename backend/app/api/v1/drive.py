from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.integrations import (
    get_google_account,
    get_valid_access_token,
)
from app.core.dependencies import (
    WorkspaceContext,
    get_workspace_context,
)
from app.db.session import get_db
from app.integrations.google import GoogleWorkspaceClient


router = APIRouter(
    prefix="/drive",
    tags=["drive"],
)


@router.get("/files")
async def list_drive_files(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    """Get recently modified files from Google Drive."""

    account = await get_google_account(
        ctx=ctx,
        db=db,
        active_only=True,
    )

    if not account or not account.access_token:
        return {
            "connected": False,
            "files": [],
            "detail": "Google account is not connected.",
        }

    access_token = await get_valid_access_token(
        account,
        db,
    )

    if not access_token:
        return {
            "connected": False,
            "files": [],
            "detail": "Google token could not be refreshed.",
        }

    client = GoogleWorkspaceClient(access_token)

    files = await client.list_recent_drive_files(
        max_results=5,
    )

    return {
        "connected": True,
        "count": len(files),
        "files": files,
    }