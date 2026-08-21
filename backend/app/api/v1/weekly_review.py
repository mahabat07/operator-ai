from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.enums import CommitmentStatus, TaskStatus
from app.models.commitment import Commitment
from app.models.task import Task

router = APIRouter(prefix="/weekly-review", tags=["weekly_review"])

_SYSTEM_PROMPT = """Summarize the user's week for an AI Chief-of-Staff weekly review.
Return ONLY JSON: {"summary": "2-3 sentences", "wins": ["..."], "at_risk": ["..."]}"""


@router.get("")
async def get_weekly_review(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    week_ago = date.today() - timedelta(days=7)
    ws = ctx.workspace_id

    completed = (await db.execute(select(Task).where(
        Task.workspace_id == ws, Task.status == TaskStatus.done, Task.completed_at.is_not(None),
        Task.completed_at >= week_ago,
    ))).scalars().all()
    overdue = (await db.execute(select(Task).where(
        Task.workspace_id == ws, Task.status != TaskStatus.done, Task.deadline.is_not(None), Task.deadline < date.today(),
    ))).scalars().all()
    open_commitments = (await db.execute(select(Commitment).where(
        Commitment.workspace_id == ws, Commitment.status == CommitmentStatus.open,
    ))).scalars().all()

    stats = {
        "completed_this_week": len(completed),
        "overdue": len(overdue),
        "open_commitments": len(open_commitments),
    }
    prompt = (
        f"Completed tasks: {[t.title for t in completed]}\n"
        f"Overdue tasks: {[t.title for t in overdue]}\n"
        f"Open commitments: {[c.title for c in open_commitments]}\n"
    )
    ai = await get_ai_provider().complete_json(_SYSTEM_PROMPT, prompt)
    return {"stats": stats, "ai_summary": ai.get("summary"), "wins": ai.get("wins", []), "at_risk": ai.get("at_risk", [])}
