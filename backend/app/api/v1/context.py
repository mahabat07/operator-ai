from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import build_context
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db

router = APIRouter(prefix="/context", tags=["context"])


@router.get("")
async def get_context(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    return await build_context(db, ctx.workspace_id, ctx.user.id)
