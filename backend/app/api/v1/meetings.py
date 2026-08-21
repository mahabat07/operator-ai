import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.calendar import Meeting
from app.models.knowledge import KnowledgeChunk
from app.repositories.base import WorkspaceScopedRepository
from sqlalchemy import select

router = APIRouter(prefix="/meetings", tags=["meetings"])

_PREP_SYSTEM_PROMPT = """You prepare a short pre-meeting briefing for a Chief of Staff product.
Given the meeting title and a few related knowledge snippets, return ONLY JSON:
{"executive_summary": "...", "talking_points": ["...", "..."]}"""

_FOLLOWUP_SYSTEM_PROMPT = """Extract action items from meeting notes. Return ONLY JSON:
{"follow_ups": ["...", "..."]}"""


class MeetingPrepRequest(BaseModel):
    title: str
    calendar_event_id: uuid.UUID | None = None


class MeetingNotesRequest(BaseModel):
    notes: str


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[Meeting]:
    return WorkspaceScopedRepository(Meeting, db)


@router.get("")
async def list_meetings(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=100)
    return [{"id": str(i.id), "title": i.title, "prep_brief": i.prep_brief, "notes": i.notes,
             "extracted_follow_ups": i.extracted_follow_ups} for i in items]


async def _find_related_knowledge(db: AsyncSession, workspace_id, query: str, limit: int = 5) -> list[KnowledgeChunk]:
    """Vector similarity search when the configured provider supports
    embeddings; falls back to simple keyword overlap otherwise (e.g.
    AI_PROVIDER=anthropic or none). Either path returns real, stored
    chunks - never invented context."""
    provider = get_ai_provider()
    vectors = await provider.embed_texts([query])
    if vectors:
        query_vector = vectors[0]
        rows = (await db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.workspace_id == workspace_id, KnowledgeChunk.embedding.is_not(None))
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(limit)
        )).scalars().all()
        if rows:
            return list(rows)
        # embeddings supported but nothing indexed yet with a vector - fall through to keyword search

    keywords = [w for w in query.lower().split() if len(w) > 3]
    if not keywords:
        return []
    candidates = (await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.workspace_id == workspace_id).limit(50))).scalars().all()
    return [r for r in candidates if any(k in r.chunk_text.lower() or k in r.title.lower() for k in keywords)][:limit]


@router.post("/prep", status_code=201)
async def prepare_meeting(payload: MeetingPrepRequest, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    """Retrieves related knowledge chunks (vector search if embeddings are
    configured, keyword match otherwise) and asks the AI to draft a
    briefing grounded in them, with citations back to their titles."""
    related = await _find_related_knowledge(db, ctx.workspace_id, payload.title)

    context_text = "\n".join(f"[{r.title}] {r.chunk_text[:300]}" for r in related) or "(no related knowledge found)"
    result = await get_ai_provider().complete_json(_PREP_SYSTEM_PROMPT, f"Meeting: {payload.title}\nContext:\n{context_text}")

    brief = result.get("executive_summary") or "No AI provider configured - connect knowledge sources and set AI_PROVIDER to get a real briefing."
    talking_points = result.get("talking_points", [])

    item = await _repo(db).create(
        ctx.workspace_id, calendar_event_id=payload.calendar_event_id, title=payload.title,
        prep_brief=brief, created_by=ctx.user.id,
    )
    return {"id": str(item.id), "title": item.title, "prep_brief": brief, "talking_points": talking_points,
            "source_citations": [r.title for r in related]}


@router.post("/{meeting_id}/notes")
async def add_notes_and_extract_followups(meeting_id: uuid.UUID, payload: MeetingNotesRequest, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    result = await get_ai_provider().complete_json(_FOLLOWUP_SYSTEM_PROMPT, payload.notes)
    follow_ups = result.get("follow_ups", [])
    item = await _repo(db).update(ctx.workspace_id, meeting_id, notes=payload.notes, extracted_follow_ups=follow_ups)
    return {"id": str(item.id), "extracted_follow_ups": follow_ups}
