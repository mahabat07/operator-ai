from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.commitment import Commitment, WaitingFor
from app.models.enums import CommitmentStatus, TaskStatus, WaitingForStatus
from app.models.task import Task

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("")
async def get_deadlines(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    ws = ctx.workspace_id
    tasks = (await db.execute(select(Task).where(
        Task.workspace_id == ws, Task.deadline.is_not(None), Task.status != TaskStatus.done
    ))).scalars().all()
    commitments = (await db.execute(select(Commitment).where(
        Commitment.workspace_id == ws, Commitment.deadline.is_not(None), Commitment.status == CommitmentStatus.open
    ))).scalars().all()
    waiting = (await db.execute(select(WaitingFor).where(
        WaitingFor.workspace_id == ws, WaitingFor.expected_by.is_not(None), WaitingFor.status == WaitingForStatus.waiting
    ))).scalars().all()

    items = (
        [{"kind": "task", "id": str(t.id), "title": t.title, "date": t.deadline, "priority": t.priority.value} for t in tasks]
        + [{"kind": "commitment", "id": str(c.id), "title": c.title, "date": c.deadline, "priority": None} for c in commitments]
        + [{"kind": "waiting_for", "id": str(w.id), "title": w.title, "date": w.expected_by, "priority": None} for w in waiting]
    )
    items.sort(key=lambda i: i["date"])
    today = date.today()
    for i in items:
        i["is_overdue"] = i["date"] < today
        i["date"] = i["date"].isoformat()
    return {"deadlines": items}
