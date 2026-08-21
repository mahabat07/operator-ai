import enum


class WorkspaceRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class AuthProvider(str, enum.Enum):
    password = "password"
    google = "google"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class PrioritySource(str, enum.Enum):
    """Did a human set this priority, or did the AI infer it? Kept explicit
    so the UI can show 'AI suggested' and the user can always override -
    this is the fix for the previous project's core complaint."""
    user = "user"
    ai = "ai"
    default = "default"


class ProjectStatus(str, enum.Enum):
    planning = "planning"
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class CommitmentStatus(str, enum.Enum):
    open = "open"
    completed = "completed"
    cancelled = "cancelled"
    overdue = "overdue"


class WaitingForStatus(str, enum.Enum):
    waiting = "waiting"
    received = "received"
    cancelled = "cancelled"
    overdue = "overdue"


class RiskSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskStatus(str, enum.Enum):
    open = "open"
    mitigating = "mitigating"
    resolved = "resolved"
    dismissed = "dismissed"


class OpportunityStatus(str, enum.Enum):
    new = "new"
    exploring = "exploring"
    pursuing = "pursuing"
    closed = "closed"
    dismissed = "dismissed"


class MemoryType(str, enum.Enum):
    preference = "preference"
    fact = "fact"
    decision = "decision"
    relationship = "relationship"
    project_context = "project_context"
    instruction = "instruction"
    other = "other"


class InboxType(str, enum.Enum):
    idea = "idea"
    task = "task"
    note = "note"
    follow_up = "follow_up"
    reminder = "reminder"
    message = "message"


class InboxStatus(str, enum.Enum):
    unprocessed = "unprocessed"
    converted = "converted"
    dismissed = "dismissed"


class InboxSource(str, enum.Enum):
    manual = "manual"
    email = "email"
    meeting = "meeting"
    slack = "slack"


class NotificationType(str, enum.Enum):
    task_overdue = "task_overdue"
    deadline_approaching = "deadline_approaching"
    waiting_for_overdue = "waiting_for_overdue"
    meeting_follow_up = "meeting_follow_up"
    weekly_review_ready = "weekly_review_ready"
    ai_insight = "ai_insight"
    other = "other"


class AutomationTrigger(str, enum.Enum):
    task_overdue = "task_overdue"
    deadline_approaching = "deadline_approaching"
    waiting_for_overdue = "waiting_for_overdue"
    meeting_finished = "meeting_finished"
    weekly_schedule = "weekly_schedule"


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class IntegrationProvider(str, enum.Enum):
    google = "google"


class KnowledgeSourceType(str, enum.Enum):
    document = "document"
    email = "email"
    meeting_note = "meeting_note"
    manual = "manual"
