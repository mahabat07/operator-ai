from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.commitment import Commitment, WaitingFor
from app.models.enums import (
    CommitmentStatus,
    ProjectStatus,
    RiskStatus,
    TaskStatus,
    WaitingForStatus,
)
from app.models.project import Project
from app.models.risk import Risk
from app.models.task import Task

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


_BRIEFING_SYSTEM_PROMPT = """
You are the AI Chief of Staff inside an Operator AI dashboard.

Write a short morning briefing based ONLY on the supplied real data.

Rules:
- 2-4 short sentences.
- Plain text only.
- Same language as the task titles when possible.
- Mention the most important/urgent task first.
- If there are no urgent tasks, say what deserves attention next.
- Do not invent tasks, deadlines, projects, risks or numbers.
- Do not say that the AI is unavailable.
"""


def task_to_dict(task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "priority": (
            task.priority.value
            if hasattr(task.priority, "value")
            else str(task.priority)
        ),
        "priority_source": (
            task.priority_source.value
            if hasattr(task.priority_source, "value")
            else str(task.priority_source)
            if task.priority_source
            else None
        ),
        "priority_score": task.priority_score,
        "priority_reason": task.priority_reason,
        "status": (
            task.status.value
            if hasattr(task.status, "value")
            else str(task.status)
        ),
        "deadline": task.deadline.isoformat() if task.deadline else None,
    }


@router.get("")
async def get_dashboard(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    ws = ctx.workspace_id

    active_statuses = [
        TaskStatus.todo,
        TaskStatus.in_progress,
    ]

    async def count(model, *conditions):
        result = await db.execute(
            select(func.count())
            .select_from(model)
            .where(
                model.workspace_id == ws,
                *conditions,
            )
        )
        return result.scalar_one()

    # ---------------------------------------------------------
    # REAL DATABASE METRICS
    # ---------------------------------------------------------

    open_tasks = await count(
        Task,
        Task.status.in_(active_statuses),
    )

    completed_today = await count(
        Task,
        Task.status == TaskStatus.done,
        Task.completed_at.is_not(None),
        func.date(Task.completed_at) == today,
    )

    overdue = await count(
        Task,
        Task.deadline.is_not(None),
        Task.deadline < today,
        Task.status.in_(active_statuses),
    )

    active_projects = await count(
        Project,
        Project.status == ProjectStatus.active,
    )

    upcoming_deadlines = await count(
        Task,
        Task.deadline.is_not(None),
        Task.deadline > today,
        Task.status.in_(active_statuses),
    )

    open_commitments = await count(
        Commitment,
        Commitment.status == CommitmentStatus.open,
    )

    waiting_for_count = await count(
        WaitingFor,
        WaitingFor.status == WaitingForStatus.waiting,
    )

    risks_count = await count(
        Risk,
        Risk.status == RiskStatus.open,
    )

    # ---------------------------------------------------------
    # TODAY
    # ---------------------------------------------------------

    today_result = await db.execute(
        select(Task)
        .where(
            Task.workspace_id == ws,
            Task.status.in_(active_statuses),
            Task.deadline == today,
        )
        .order_by(
            Task.priority_score.desc().nullslast(),
            Task.deadline.asc(),
        )
        .limit(10)
    )

    today_tasks = [
        task_to_dict(task)
        for task in today_result.scalars().all()
    ]

    # ---------------------------------------------------------
    # OVERDUE
    # ---------------------------------------------------------

    overdue_result = await db.execute(
        select(Task)
        .where(
            Task.workspace_id == ws,
            Task.status.in_(active_statuses),
            Task.deadline.is_not(None),
            Task.deadline < today,
        )
        .order_by(
            Task.priority_score.desc().nullslast(),
            Task.deadline.asc(),
        )
        .limit(10)
    )

    overdue_tasks = [
        task_to_dict(task)
        for task in overdue_result.scalars().all()
    ]

    # ---------------------------------------------------------
    # UPCOMING
    # ---------------------------------------------------------

    upcoming_result = await db.execute(
        select(Task)
        .where(
            Task.workspace_id == ws,
            Task.status.in_(active_statuses),
            Task.deadline.is_not(None),
            Task.deadline > today,
        )
        .order_by(
            Task.deadline.asc(),
            Task.priority_score.desc().nullslast(),
        )
        .limit(10)
    )

    upcoming_tasks = [
        task_to_dict(task)
        for task in upcoming_result.scalars().all()
    ]

    # ---------------------------------------------------------
    # IMPORTANT TASKS
    # ---------------------------------------------------------

    important_result = await db.execute(
        select(Task)
        .where(
            Task.workspace_id == ws,
            Task.status.in_(active_statuses),
        )
        .order_by(
            Task.priority_score.desc().nullslast(),
            Task.deadline.asc().nullslast(),
        )
        .limit(8)
    )

    important_tasks = [
        task_to_dict(task)
        for task in important_result.scalars().all()
    ]

    # ---------------------------------------------------------
    # COMMITMENTS
    # ---------------------------------------------------------

    commitments_result = await db.execute(
        select(Commitment)
        .where(
            Commitment.workspace_id == ws,
            Commitment.status == CommitmentStatus.open,
        )
        .limit(5)
    )

    commitments = []

    for item in commitments_result.scalars().all():
        commitments.append(
            {
                "id": str(item.id),
                "title": item.title,
                "deadline": (
                    item.deadline.isoformat()
                    if item.deadline
                    else None
                ),
            }
        )

    # ---------------------------------------------------------
    # WAITING FOR
    # ---------------------------------------------------------

    waiting_result = await db.execute(
        select(WaitingFor)
        .where(
            WaitingFor.workspace_id == ws,
            WaitingFor.status == WaitingForStatus.waiting,
        )
        .limit(5)
    )

    waiting_for = []

    for item in waiting_result.scalars().all():
        waiting_for.append(
            {
                "id": str(item.id),
                "title": item.title,
                "expected_by": (
                    item.expected_by.isoformat()
                    if item.expected_by
                    else None
                ),
            }
        )

    # ---------------------------------------------------------
    # AI MORNING BRIEF
    # ---------------------------------------------------------

    briefing = None

    briefing_data = {
        "today": today.isoformat(),
        "metrics": {
            "open_tasks": open_tasks,
            "completed_today": completed_today,
            "overdue": overdue,
            "active_projects": active_projects,
            "upcoming_deadlines": upcoming_deadlines,
            "open_commitments": open_commitments,
            "waiting_for": waiting_for_count,
            "risks": risks_count,
        },
        "important_tasks": important_tasks[:5],
        "today_tasks": today_tasks,
        "overdue_tasks": overdue_tasks,
        "upcoming_tasks": upcoming_tasks[:5],
    }

    try:
        provider = get_ai_provider()

        result = await provider.complete_json(
            _BRIEFING_SYSTEM_PROMPT,
            str(briefing_data),
        )

        if result:
            briefing = (
                result.get("morning_brief")
                or result.get("summary")
                or result.get("briefing")
                or result.get("content")
            )

    except Exception:
        briefing = None

    # ---------------------------------------------------------
    # DETERMINISTIC FALLBACK
    # ---------------------------------------------------------

    if not briefing:
        if overdue_tasks:
            first = overdue_tasks[0]
            briefing = (
                f"Сначала обрати внимание на просроченную задачу "
                f"«{first['title']}». "
            )
        elif today_tasks:
            first = today_tasks[0]
            briefing = (
                f"Сегодня главное — задача «{first['title']}». "
            )
        elif important_tasks:
            first = important_tasks[0]
            briefing = (
                f"Сейчас наиболее важная задача — "
                f"«{first['title']}». "
            )
        else:
            briefing = (
                "Активных задач с ближайшими дедлайнами сейчас нет. "
                "Можно сосредоточиться на планировании следующих шагов."
            )

        if upcoming_tasks:
            briefing += (
                f" В ближайшее время ожидается "
                f"{len(upcoming_tasks)} задача с дедлайном."
            )

    # ---------------------------------------------------------
    # FINAL RESPONSE
    # ---------------------------------------------------------

    return {
        "today": {
            "tasks": today_tasks,
            "overdue_tasks": overdue_tasks,
            "upcoming_tasks": upcoming_tasks,
            "important_tasks": important_tasks,
            "commitments": commitments,
            "waiting_for": waiting_for,
        },
        "metrics": {
            "open_tasks": open_tasks,
            "completed_today": completed_today,
            "overdue": overdue,
            "active_projects": active_projects,
            "upcoming_deadlines": upcoming_deadlines,
            "open_commitments": open_commitments,
            "waiting_for": waiting_for_count,
            "risks": risks_count,
        },
        "ai_briefing": briefing,
    }
