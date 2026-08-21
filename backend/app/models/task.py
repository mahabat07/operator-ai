import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import ARRAY, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin
from app.models.enums import Priority, PrioritySource, TaskStatus


class Task(WorkspaceScopedMixin, Base):
    __tablename__ = "tasks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), default=TaskStatus.todo)

    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="task_priority"), default=Priority.medium)
    priority_source: Mapped[PrioritySource] = mapped_column(
        Enum(PrioritySource, name="task_priority_source"), default=PrioritySource.default
    )
    priority_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="0-100, from ai/prioritizer.py")
    priority_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="human-readable 'why' shown in UI")

    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    depends_on_task_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)

    source_inbox_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
