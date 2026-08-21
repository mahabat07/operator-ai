import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment import WaitingFor
from app.models.enums import AutomationTrigger, NotificationType, TaskStatus, WaitingForStatus
from app.models.system import Automation, Notification
from app.models.task import Task


async def _due_task_overdue(db: AsyncSession, workspace_id: uuid.UUID) -> list[Task]:
    return list((await db.execute(select(Task).where(
        Task.workspace_id == workspace_id, Task.status != TaskStatus.done,
        Task.deadline.is_not(None), Task.deadline < date.today(),
    ))).scalars().all())


async def _due_waiting_for_overdue(db: AsyncSession, workspace_id: uuid.UUID) -> list[WaitingFor]:
    return list((await db.execute(select(WaitingFor).where(
        WaitingFor.workspace_id == workspace_id, WaitingFor.status == WaitingForStatus.waiting,
        WaitingFor.expected_by.is_not(None), WaitingFor.expected_by < date.today(),
    ))).scalars().all())


async def run_workspace_automations(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    automations = list((await db.execute(select(Automation).where(
        Automation.workspace_id == workspace_id, Automation.is_active == True,  # noqa: E712
    ))).scalars().all())

    created = 0
    for automation in automations:
        if automation.trigger == AutomationTrigger.task_overdue:
            for task in await _due_task_overdue(db, workspace_id):
                db.add(Notification(
                    workspace_id=workspace_id, user_id=task.created_by, type=NotificationType.task_overdue,
                    title=f"Overdue: {task.title}", related_entity_type="task", related_entity_id=task.id,
                ))
                created += 1
        elif automation.trigger == AutomationTrigger.waiting_for_overdue:
            for item in await _due_waiting_for_overdue(db, workspace_id):
                db.add(Notification(
                    workspace_id=workspace_id, user_id=item.created_by, type=NotificationType.waiting_for_overdue,
                    title=f"Still waiting on: {item.title}", related_entity_type="waiting_for", related_entity_id=item.id,
                ))
                created += 1
        automation.last_run_at = date.today()

    await db.commit()
    return created
