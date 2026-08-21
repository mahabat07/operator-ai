import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prioritizer import score_priority
from app.ai.provider import get_ai_provider
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.enums import Priority, PrioritySource, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Task]:
    return WorkspaceScopedRepository(Task, db)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status_: TaskStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    page: int = 1,
    limit: int = 20,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    tasks = await _repo(db).list(
        ctx.workspace_id, limit=limit, offset=(page - 1) * limit,
        status=status_, priority=priority, project_id=project_id, assignee_id=assignee_id,
    )
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    payload: TaskCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)
):

    data = payload.model_dump()

    business_impact = None
    if data.get("project_id"):
        project = (await db.execute(select(Project).where(Project.id == data["project_id"]))).scalar_one_or_none()
        business_impact = project.business_impact if project else None

    if data.get("priority"):
        data["priority_source"] = PrioritySource.user
    else:
        scored = await score_priority(
            get_ai_provider(), title=data["title"], description=data.get("description"),
            deadline=data.get("deadline"), business_impact=business_impact,
        )
        data["priority"] = scored["priority"]
        data["priority_source"] = scored["source"]
        data["priority_score"] = scored["score"]
        data["priority_reason"] = scored["reason"]

    task = await _repo(db).create(ctx.workspace_id, created_by=ctx.user.id, **data)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    task = await _repo(db).get(ctx.workspace_id, task_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID, payload: TaskUpdate,
    ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == TaskStatus.done:
        data["completed_at"] = datetime.now(timezone.utc)
    if data.get("priority"):
        data["priority_source"] = PrioritySource.user  # manual edit always overrides AI's guess
    task = await _repo(db).update(ctx.workspace_id, task_id, **data)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/reprioritize", response_model=TaskResponse)
async def reprioritize_task(
    task_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)
):
    """Explicitly ask the AI to (re)score an existing task - e.g. after
    editing its description or deadline."""
    task = await _repo(db).get(ctx.workspace_id, task_id)
    business_impact = None
    if task.project_id:
        project = (await db.execute(select(Project).where(Project.id == task.project_id))).scalar_one_or_none()
        business_impact = project.business_impact if project else None
    scored = await score_priority(
        get_ai_provider(), title=task.title, description=task.description,
        deadline=task.deadline, business_impact=business_impact,
    )
    task = await _repo(db).update(
        ctx.workspace_id, task_id, priority=scored["priority"], priority_source=scored["source"],
        priority_score=scored["score"], priority_reason=scored["reason"],
    )
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    await _repo(db).delete(ctx.workspace_id, task_id)
