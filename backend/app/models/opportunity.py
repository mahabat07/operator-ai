import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import OpportunityStatus


class Opportunity(WorkspaceScopedMixin, Base):
    __tablename__ = "opportunities"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OpportunityStatus] = mapped_column(Enum(OpportunityStatus, name="opportunity_status"), default=OpportunityStatus.new)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    detected_by: Mapped[str] = mapped_column(String(20), default="ai")
