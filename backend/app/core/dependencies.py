import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMember

_bearer = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@dataclass
class WorkspaceContext:
    user: User
    workspace_id: uuid.UUID


async def get_workspace_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceContext:
    """Resolves the active workspace for this request and checks membership.
    Every workspace-scoped repository call takes ctx.workspace_id, which is
    how tenant isolation is enforced end to end (see repositories/base.py)."""
    if user.current_workspace_id is None:
        raise HTTPException(status_code=400, detail="No active workspace")

    member = (
        await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == user.current_workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return WorkspaceContext(user=user, workspace_id=user.current_workspace_id)
