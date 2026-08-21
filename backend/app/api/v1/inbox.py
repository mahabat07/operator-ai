import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.ai.tools import execute_tool
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.enums import InboxStatus
from app.models.system import InboxItem
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import InboxCreate, InboxResponse

router = APIRouter(prefix="/inbox", tags=["inbox"])

_CLASSIFY_SYSTEM_PROMPT = """You triage a quick capture note for an AI Chief-of-Staff.
Return ONLY JSON: {"type": "task"|"note"|"follow_up"|"reminder"|"message"|"idea",
"title": "<short title>", "priority": "low"|"medium"|"high"|"urgent",
"deadline": "YYYY-MM-DD or null", "person": "<name mentioned, or null>"}"""


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[InboxItem]:
    return WorkspaceScopedRepository(InboxItem, db)


@router.get("", response_model=list[InboxResponse])
async def list_inbox(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=100)
    return [InboxResponse.model_validate(i) for i in items]


@router.post("", response_model=InboxResponse, status_code=201)
async def create_inbox_item(payload: InboxCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    """Quick-capture: raw text in, AI classification suggestion out. The
    user confirms (or edits) before anything is created - human-in-the-loop
    per the product's core principle."""
    provider = get_ai_provider()
    suggestion = await provider.complete_json(_CLASSIFY_SYSTEM_PROMPT, payload.raw_text)
    item = await _repo(db).create(
        ctx.workspace_id, created_by=ctx.user.id, raw_text=payload.raw_text,
        type=suggestion.get("type"), ai_suggestion=suggestion,
    )
    return InboxResponse.model_validate(item)


@router.post("/{item_id}/dismiss", response_model=InboxResponse)
async def dismiss_inbox_item(item_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    item = await _repo(db).update(ctx.workspace_id, item_id, status=InboxStatus.dismissed)
    return InboxResponse.model_validate(item)


@router.post("/{item_id}/confirm", response_model=InboxResponse)
async def confirm_inbox_item(item_id: uuid.UUID, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    """Converts the capture into a real object via ai/tools.execute_tool -
    the SAME function the assistant chat uses, and the same one that runs
    score_priority() for tasks. No duplicated, divergent priority logic."""
    item = await _repo(db).get(ctx.workspace_id, item_id)
    if item.status == InboxStatus.converted:
        return InboxResponse.model_validate(item)

    suggestion = item.ai_suggestion or {}
    item_type = suggestion.get("type") or (item.type.value if item.type else None)
    title = suggestion.get("title") or item.raw_text[:200]
    args = {"title": title}

    if item_type in {"task", "reminder", "follow_up", "idea"} or item_type is None:
        args.update({
            "description": item.raw_text if item.raw_text != title else None,
            "priority": suggestion.get("priority"),  # None -> tools.py runs the AI prioritizer
            "deadline": suggestion.get("deadline"),
        })
        outcome = await execute_tool(db, ctx.workspace_id, ctx.user.id, "create_task", args)
    elif item_type == "message":
        outcome = await execute_tool(db, ctx.workspace_id, ctx.user.id, "create_commitment",
                                      {"title": title, "related_person": suggestion.get("person")})
    else:  # "note" - stays in Inbox until explicitly dismissed
        return InboxResponse.model_validate(item)

    item.status = InboxStatus.converted
    item.converted_to_type = outcome.get("type")
    item.converted_to_id = uuid.UUID(outcome["id"])
    await db.commit()
    await db.refresh(item)
    return InboxResponse.model_validate(item)
