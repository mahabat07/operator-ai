import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.system import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Notification).where(Notification.workspace_id == ctx.workspace_id, Notification.user_id == ctx.user.id)
        .order_by(Notification.created_at.desc()).limit(100)
    )).scalars().all()
    return [{"id": str(n.id), "type": n.type.value, "title": n.title, "body": n.body, "is_read": n.is_read,
             "created_at": n.created_at.isoformat()} for n in rows]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    n = (await db.execute(select(Notification).where(
        Notification.id == notification_id, Notification.workspace_id == ctx.workspace_id
    ))).scalar_one()
    n.is_read = True
    await db.commit()
    return {"id": str(n.id), "is_read": True}
