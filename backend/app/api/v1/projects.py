import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.project import Project
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Project]:
    return WorkspaceScopedRepository(Project, db)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=200)
    return [ProjectResponse.model_validate(i) for i in items]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(payload: ProjectCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).create(ctx.workspace_id, owner_id=ctx.user.id, **payload.model_dump())
    return ProjectResponse.model_validate(item)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).get(ctx.workspace_id, project_id)
    return ProjectResponse.model_validate(item)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    await _repo(db).delete(ctx.workspace_id, project_id)
