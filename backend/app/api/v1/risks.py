import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.enums import RiskStatus
from app.models.risk import Risk
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import RiskResponse

router = APIRouter(prefix="/risks", tags=["risks"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Risk]:
    return WorkspaceScopedRepository(Risk, db)


@router.get("", response_model=list[RiskResponse])
async def list_risks(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=100)
    return [RiskResponse.model_validate(i) for i in items]


@router.post("/{risk_id}/dismiss", response_model=RiskResponse)
async def dismiss_risk(risk_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).update(ctx.workspace_id, risk_id, status=RiskStatus.dismissed)
    return RiskResponse.model_validate(item)
