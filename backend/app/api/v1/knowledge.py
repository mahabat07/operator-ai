from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.knowledge import KnowledgeChunk
from app.repositories.base import WorkspaceScopedRepository
from app.schemas.domain import KnowledgeCreate

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[KnowledgeChunk]:
    return WorkspaceScopedRepository(KnowledgeChunk, db)


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    step = max(chunk_size - overlap, 1)
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), step)]


@router.get("")
async def list_knowledge(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    items = await _repo(db).list(ctx.workspace_id, limit=100)
    return [{"id": str(i.id), "title": i.title, "source_type": i.source_type.value, "chunk_index": i.chunk_index,
             "has_embedding": i.embedding is not None} for i in items]


@router.post("", status_code=201)
async def index_document(payload: KnowledgeCreate, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    """Chunks the document, embeds every chunk (if the configured AI
    provider supports embeddings - currently OpenAI only), and stores it.
    When no embeddings provider is available, chunks are still stored and
    remain searchable via keyword match (see meetings.py::prepare_meeting) -
    embeddings just aren't required for the feature to work at all."""
    chunks = _chunk_text(payload.content)
    vectors = await get_ai_provider().embed_texts(chunks)

    created = []
    for idx, chunk in enumerate(chunks):
        embedding = vectors[idx] if vectors else None
        item = await _repo(db).create(
            ctx.workspace_id, source_type=payload.source_type, title=payload.title,
            chunk_text=chunk, chunk_index=idx, embedding=embedding,
        )
        created.append(str(item.id))
    return {"indexed_chunks": created, "embedded": vectors is not None}
