import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.commitment import Commitment
from app.models.enums import CommitmentStatus
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import CommitmentCreate, CommitmentResponse

router = APIRouter(prefix="/commitments", tags=["commitments"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Commitment]:
    return WorkspaceScopedRepository(Commitment, db)


@router.get("", response_model=list[CommitmentResponse])
async def list_commitments(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=200)
    return [CommitmentResponse.model_validate(i) for i in items]


@router.post("", response_model=CommitmentResponse, status_code=201)
async def create_commitment(payload: CommitmentCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).create(ctx.workspace_id, created_by=ctx.user.id, **payload.model_dump())
    return CommitmentResponse.model_validate(item)


@router.post("/{commitment_id}/complete", response_model=CommitmentResponse)
async def complete_commitment(commitment_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).update(ctx.workspace_id, commitment_id, status=CommitmentStatus.completed)
    return CommitmentResponse.model_validate(item)
