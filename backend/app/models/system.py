import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import AutomationTrigger, InboxSource, InboxStatus, InboxType, NotificationType


class InboxItem(WorkspaceScopedMixin, Base):

    __tablename__ = "inbox_items"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[InboxSource] = mapped_column(Enum(InboxSource, name="inbox_source"), default=InboxSource.manual)
    type: Mapped[Optional[InboxType]] = mapped_column(Enum(InboxType, name="inbox_type"), nullable=True)
    ai_suggestion: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[InboxStatus] = mapped_column(Enum(InboxStatus, name="inbox_status"), default=InboxStatus.unprocessed)
    converted_to_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    converted_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class Notification(WorkspaceScopedMixin, Base):
    __tablename__ = "notifications"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), default=NotificationType.other)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class Automation(WorkspaceScopedMixin, Base):
    __tablename__ = "automations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger: Mapped[AutomationTrigger] = mapped_column(Enum(AutomationTrigger, name="automation_trigger"))
    action: Mapped[str] = mapped_column(String(50), default="notify", comment="notify|create_task|send_digest")
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class IntegrationAccount(WorkspaceScopedMixin, Base):

    __tablename__ = "integration_accounts"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="google")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="encrypted at rest in production - see SECURITY.md")
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
