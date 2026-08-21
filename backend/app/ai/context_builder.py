from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment import Commitment, WaitingFor
from app.models.enums import CommitmentStatus, TaskStatus, WaitingForStatus
from app.models.task import Task


def _task_dict(t: Task) -> dict:
    return {
        "id": str(t.id), "title": t.title, "priority": t.priority.value,
        "priority_score": t.priority_score, "deadline": t.deadline.isoformat() if t.deadline else None,
        "status": t.status.value, "project_id": str(t.project_id) if t.project_id else None,
    }


def _commitment_dict(c: Commitment) -> dict:
    return {
        "id": str(c.id), "title": c.title, "related_person": c.related_person,
        "deadline": c.deadline.isoformat() if c.deadline else None, "priority": "medium",
    }


async def build_context(db: AsyncSession, workspace_id, user_id) -> dict:
    today = date.today()
    soon = today + timedelta(days=7)

    overdue = (await db.execute(
        select(Task).where(Task.workspace_id == workspace_id,
                            Task.status.in_([TaskStatus.todo, TaskStatus.in_progress]),
                            Task.deadline.is_not(None), Task.deadline < today)
    )).scalars().all()
    due_today = (await db.execute(
        select(Task).where(Task.workspace_id == workspace_id, Task.status != TaskStatus.done, Task.deadline == today)
    )).scalars().all()
    upcoming = (await db.execute(
        select(Task).where(Task.workspace_id == workspace_id, Task.status != TaskStatus.done,
                            Task.deadline.is_not(None), Task.deadline > today, Task.deadline <= soon)
    )).scalars().all()
    commitments = (await db.execute(
        select(Commitment).where(Commitment.workspace_id == workspace_id, Commitment.status == CommitmentStatus.open)
    )).scalars().all()
    waiting = (await db.execute(
        select(WaitingFor).where(WaitingFor.workspace_id == workspace_id, WaitingFor.status == WaitingForStatus.waiting)
    )).scalars().all()

    all_active = (await db.execute(
        select(Task).where(
            Task.workspace_id == workspace_id,
            Task.status.in_([TaskStatus.todo, TaskStatus.in_progress]),
        ).order_by(
            Task.priority_score.desc().nullslast(), Task.created_at.desc()
        )
    )).scalars().all()

    return {
        "all_active_tasks": [_task_dict(t) for t in all_active],
        "overdue_tasks": [_task_dict(t) for t in overdue],
        "today_tasks": [_task_dict(t) for t in due_today],
        "upcoming_tasks": [_task_dict(t) for t in upcoming],
        "open_commitments": [_commitment_dict(c) for c in commitments],
        "waiting_for": [{"id": str(w.id), "title": w.title, "related_person": w.related_person,
                          "expected_by": w.expected_by.isoformat() if w.expected_by else None} for w in waiting],
    }
