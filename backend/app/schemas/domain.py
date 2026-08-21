import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.enums import (
    CommitmentStatus, InboxStatus, InboxType, OpportunityStatus, Priority,
    PrioritySource, ProjectStatus, RiskSeverity, RiskStatus, TaskStatus,
    WaitingForStatus,
)


# ---------- Tasks ----------
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    project_id: uuid.UUID | None = None
    priority: Priority | None = None
    deadline: date | None = None
    assignee_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    deadline: date | None = None
    assignee_id: uuid.UUID | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    priority_source: PrioritySource
    priority_score: int | None
    priority_reason: str | None
    deadline: date | None
    assignee_id: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Projects ----------
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    business_impact: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    business_impact: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Commitments / Waiting For ----------
class CommitmentCreate(BaseModel):
    title: str
    description: str | None = None
    related_person: str | None = None
    deadline: date | None = None


class CommitmentResponse(BaseModel):
    id: uuid.UUID
    title: str
    related_person: str | None
    deadline: date | None
    status: CommitmentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class WaitingForCreate(BaseModel):
    title: str
    related_person: str | None = None
    expected_by: date | None = None


class WaitingForResponse(BaseModel):
    id: uuid.UUID
    title: str
    related_person: str | None
    expected_by: date | None
    status: WaitingForStatus
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Inbox ----------
class InboxCreate(BaseModel):
    raw_text: str


class InboxResponse(BaseModel):
    id: uuid.UUID
    raw_text: str
    type: InboxType | None
    ai_suggestion: dict[str, Any] | None
    status: InboxStatus
    converted_to_type: str | None
    converted_to_id: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Risks / Opportunities ----------
class RiskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    severity: RiskSeverity
    status: RiskStatus
    recommended_action: str | None
    source_reference: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: OpportunityStatus
    recommended_action: str | None
    source_reference: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Knowledge / Memory ----------
class KnowledgeCreate(BaseModel):
    title: str
    content: str
    source_type: str = "manual"


class MemoryCreate(BaseModel):
    content: str
    type: str = "fact"
    related_entity: str | None = None


# ---------- Automations ----------
class AutomationCreate(BaseModel):
    name: str
    trigger: str
    action: str = "notify"
    config: dict[str, Any] | None = None


class AutomationResponse(BaseModel):
    id: uuid.UUID
    name: str
    trigger: str
    action: str
    is_active: bool
    last_run_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Assistant chat ----------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    actions_taken: list[dict[str, Any]] = []
