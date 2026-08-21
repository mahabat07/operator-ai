import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import CommitmentStatus, WaitingForStatus


class Commitment(WorkspaceScopedMixin, Base):
    """Something *we* promised someone else."""
    __tablename__ = "commitments"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[CommitmentStatus] = mapped_column(Enum(CommitmentStatus, name="commitment_status"), default=CommitmentStatus.open)
    source_inbox_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class WaitingFor(WorkspaceScopedMixin, Base):
    """Something *someone else* owes us."""
    __tablename__ = "waiting_for_items"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    related_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_by: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[WaitingForStatus] = mapped_column(Enum(WaitingForStatus, name="waiting_for_status"), default=WaitingForStatus.waiting)
    source_inbox_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
