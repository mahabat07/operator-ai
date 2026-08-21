import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.commitment import WaitingFor
from app.models.enums import WaitingForStatus
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import WaitingForCreate, WaitingForResponse

router = APIRouter(prefix="/waiting-for", tags=["waiting_for"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[WaitingFor]:
    return WorkspaceScopedRepository(WaitingFor, db)


@router.get("", response_model=list[WaitingForResponse])
async def list_waiting_for(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=200)
    return [WaitingForResponse.model_validate(i) for i in items]


@router.post("", response_model=WaitingForResponse, status_code=201)
async def create_waiting_for(payload: WaitingForCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).create(ctx.workspace_id, created_by=ctx.user.id, **payload.model_dump())
    return WaitingForResponse.model_validate(item)


@router.post("/{item_id}/received", response_model=WaitingForResponse)
async def mark_received(item_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).update(ctx.workspace_id, item_id, status=WaitingForStatus.received)
    return WaitingForResponse.model_validate(item)
