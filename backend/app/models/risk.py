import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import RiskSeverity, RiskStatus


class Risk(WorkspaceScopedMixin, Base):
    __tablename__ = "risks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[RiskSeverity] = mapped_column(Enum(RiskSeverity, name="risk_severity"), default=RiskSeverity.medium)
    status: Mapped[RiskStatus] = mapped_column(Enum(RiskStatus, name="risk_status"), default=RiskStatus.open)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="e.g. email/meeting this was detected from - for source citation")
    detected_by: Mapped[str] = mapped_column(String(20), default="ai", comment="ai|user")
