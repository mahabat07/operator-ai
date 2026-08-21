import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import KnowledgeSourceType

try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:  # pgvector extension not installed - falls back gracefully
    _HAS_PGVECTOR = False


class KnowledgeChunk(WorkspaceScopedMixin, Base):

    __tablename__ = "knowledge_chunks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[KnowledgeSourceType] = mapped_column(Enum(KnowledgeSourceType, name="knowledge_source_type"))
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="external id, e.g. Gmail message id")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(default=0)
    if _HAS_PGVECTOR:
        embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)
