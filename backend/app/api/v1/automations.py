import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.system import Automation
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import AutomationCreate, AutomationResponse

router = APIRouter(prefix="/automations", tags=["automations"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Automation]:
    return WorkspaceScopedRepository(Automation, db)


@router.get("", response_model=list[AutomationResponse])
async def list_automations(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=100)
    return [AutomationResponse.model_validate(i) for i in items]


@router.post("", response_model=AutomationResponse, status_code=201)
async def create_automation(payload: AutomationCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).create(ctx.workspace_id, created_by=ctx.user.id, **payload.model_dump())
    return AutomationResponse.model_validate(item)


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(automation_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    await _repo(db).delete(ctx.workspace_id, automation_id)


@router.post("/run-due")
async def run_due_automations(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    from app.workers.automation_runner import run_workspace_automations
    created = await run_workspace_automations(db, ctx.workspace_id)
    return {"notifications_created": created}
