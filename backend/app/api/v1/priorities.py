from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import build_context
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db

router = APIRouter(prefix="/priorities", tags=["priorities"])

_PRIORITY_RANK = {"urgent": 3, "high": 2, "medium": 1, "low": 0}


@router.get("")
async def get_priorities(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    context = await build_context(db, ctx.workspace_id, ctx.user.id)
    today = date.today()

    candidates = []
    for t in context["overdue_tasks"] + context["today_tasks"] + context["upcoming_tasks"]:
        candidates.append({**t, "kind": "task"})
    for c in context["open_commitments"]:
        candidates.append({**c, "kind": "commitment"})

    def sort_key(item):
        score = item.get("priority_score")
        if score is None:
            score = _PRIORITY_RANK.get(item.get("priority", "medium"), 1) * 25
        return score

    candidates.sort(key=sort_key, reverse=True)
    top = candidates[:10]
    for item in top:
        item["score"] = sort_key(item)
    return {"top_priorities": top}
