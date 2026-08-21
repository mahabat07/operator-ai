import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prioritizer import score_priority
from app.ai.provider import get_ai_provider
from app.models.commitment import Commitment, WaitingFor
from app.models.project import Project
from app.models.task import Task

TOOL_SCHEMAS = [
    {
        "name": "create_task",
        "description": "Create a task/to-do for the user. Priority is inferred automatically unless given explicitly.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "deadline": {"type": "string", "description": "YYYY-MM-DD, optional"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                "project_id": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "create_commitment",
        "description": "Record something the user promised to someone else.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "related_person": {"type": "string"},
                "deadline": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "create_waiting_for",
        "description": "Record something the user is waiting to receive from someone else.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "related_person": {"type": "string"},
                "expected_by": {"type": "string"},
            },
            "required": ["title"],
        },
    },
]


async def execute_tool(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, name: str, args: dict[str, Any]) -> dict:
    if name == "create_task":
        deadline = date.fromisoformat(args["deadline"]) if args.get("deadline") else None
        project_id = uuid.UUID(args["project_id"]) if args.get("project_id") else None

        business_impact = None
        if project_id:
            project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
            business_impact = project.business_impact if project else None

        blocking_count = 0  # placeholder for future dependency-graph lookups

        if args.get("priority"):
            from app.models.enums import Priority, PrioritySource
            priority, priority_source, priority_score, priority_reason = (
                Priority(args["priority"]), PrioritySource.user, None, "set explicitly",
            )
        else:
            scored = await score_priority(
                get_ai_provider(), title=args["title"], description=args.get("description"),
                deadline=deadline, business_impact=business_impact, blocking_count=blocking_count,
            )
            priority, priority_source, priority_score, priority_reason = (
                scored["priority"], scored["source"], scored["score"], scored["reason"],
            )

        task = Task(
            workspace_id=workspace_id, title=args["title"], description=args.get("description"),
            deadline=deadline, project_id=project_id, priority=priority, priority_source=priority_source,
            priority_score=priority_score, priority_reason=priority_reason, created_by=user_id,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return {"type": "task", "id": str(task.id), "title": task.title, "priority": task.priority.value}

    if name == "create_commitment":
        deadline = date.fromisoformat(args["deadline"]) if args.get("deadline") else None
        commitment = Commitment(
            workspace_id=workspace_id, title=args["title"], related_person=args.get("related_person"),
            deadline=deadline, created_by=user_id,
        )
        db.add(commitment)
        await db.commit()
        await db.refresh(commitment)
        return {"type": "commitment", "id": str(commitment.id), "title": commitment.title}

    if name == "create_waiting_for":
        expected_by = date.fromisoformat(args["expected_by"]) if args.get("expected_by") else None
        item = WaitingFor(
            workspace_id=workspace_id, title=args["title"], related_person=args.get("related_person"),
            expected_by=expected_by, created_by=user_id,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return {"type": "waiting_for", "id": str(item.id), "title": item.title}

    raise ValueError(f"Unknown tool: {name}")
