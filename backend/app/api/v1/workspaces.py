import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    role: WorkspaceRole

    class Config:
        from_attributes = True


class WorkspaceCreate(BaseModel):
    name: str


class SwitchWorkspace(BaseModel):
    workspace_id: uuid.UUID


@router.get("", response_model=list[WorkspaceOut])
async def list_my_workspaces(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )).all()
    return [WorkspaceOut(id=w.id, name=w.name, role=role) for w, role in rows]


@router.post("", response_model=WorkspaceOut, status_code=201)
async def create_workspace(payload: WorkspaceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace = Workspace(name=payload.name)
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner))
    await db.commit()
    return WorkspaceOut(id=workspace.id, name=workspace.name, role=WorkspaceRole.owner)


@router.post("/switch")
async def switch_workspace(payload: SwitchWorkspace, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    member = (await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == payload.workspace_id, WorkspaceMember.user_id == user.id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    user.current_workspace_id = payload.workspace_id
    await db.commit()
    return {"current_workspace_id": str(payload.workspace_id)}
