import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.enums import OpportunityStatus
from app.models.opportunity import Opportunity
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import OpportunityResponse

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Opportunity]:
    return WorkspaceScopedRepository(Opportunity, db)


@router.get("", response_model=list[OpportunityResponse])
async def list_opportunities(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=100)
    return [OpportunityResponse.model_validate(i) for i in items]


@router.post("/{opportunity_id}/dismiss", response_model=OpportunityResponse)
async def dismiss_opportunity(opportunity_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).update(ctx.workspace_id, opportunity_id, status=OpportunityStatus.dismissed)
    return OpportunityResponse.model_validate(item)
