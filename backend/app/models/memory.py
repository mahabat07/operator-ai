import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import MemoryType


class MemoryEntry(WorkspaceScopedMixin, Base):
    __tablename__ = "memory_entries"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[MemoryType] = mapped_column(Enum(MemoryType, name="memory_type"), default=MemoryType.fact)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
