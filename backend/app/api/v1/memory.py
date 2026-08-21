from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.memory import MemoryEntry
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import MemoryCreate

router = APIRouter(prefix="/memory", tags=["memory"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[MemoryEntry]:
    return WorkspaceScopedRepository(MemoryEntry, db)


@router.get("")
async def list_memory(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=200)
    return [{"id": str(i.id), "type": i.type.value, "content": i.content, "related_entity": i.related_entity} for i in items]


@router.post("", status_code=201)
async def create_memory(payload: MemoryCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).create(ctx.workspace_id, created_by=ctx.user.id, **payload.model_dump())
    return {"id": str(item.id)}
