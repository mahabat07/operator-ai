import re
from datetime import date, datetime, timezone

from sqlalchemy import select
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import build_context
from app.ai.provider import get_ai_provider
from app.ai.tools import TOOL_SCHEMAS, execute_tool
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.enums import ChatRole, TaskStatus
from app.models.task import Task
from app.schemas.domain import ChatRequest, ChatResponse

_READ_ONLY_KEYWORDS_EN = (
    "what tasks", "what are my tasks", "what do i have", "show my tasks",
    "list my tasks", "what's most important", "what is most important",
    "which task", "what should i work on", "what's urgent",
    "what is urgent", "what's due", "what is due",
)
_READ_ONLY_KEYWORDS_RU = (
    "какие задачи", "что у меня", "что самое главное", "что является",
    "покажи задачи", "перечисли задачи", "список задач",
    "какие задачи есть", "что нужно", "что сделать",
    "какая задача", "самый важный", "самое важное",
    "самый приоритетн", "самое приоритетн",
)
_ACTION_KEYWORDS_EN = (
    "create ", "add ", "make ", "new task", "new commitment",
    "complete ", "mark done", "finish ", "delete ", "remove ",
    "cancel ", "set task", "update task", "change task",
    "remember ", "track ", "note that",
)
_ACTION_KEYWORDS_RU = (
    "создай", "создать", "добавь", "добавить", "новая задача",
    "выполни", "отметь", "заверши", "удали", "удалить",
    "отмен", "измени", "обнови", "запомни", "запиши",
    "запланируй", "напомни",
)
_OVERDUE_KEYWORDS_EN = (
    "overdue", "tasks overdue", "overdue tasks", "past due",
    "which tasks are overdue", "what tasks are overdue",
    "what is overdue", "what's overdue",
)
_OVERDUE_KEYWORDS_RU = (
    "просрочен", "просроченные задачи", "просроченные",
    "просрочено", "просроченных задач",
)


def _is_read_only_query(message: str) -> bool:
    """Detect read-only queries so the assistant never fires tools for them."""
    low = message.lower().strip()
    if any(kw in low for kw in _ACTION_KEYWORDS_EN + _ACTION_KEYWORDS_RU):
        return False
    if any(kw in low for kw in _READ_ONLY_KEYWORDS_EN + _READ_ONLY_KEYWORDS_RU):
        return True
    if "?" in low or "?" in message:
        return True
    return False


def _is_overdue_query(message: str) -> bool:
    """Detect queries specifically asking about overdue tasks."""
    low = message.lower().strip()
    if any(kw in low for kw in _OVERDUE_KEYWORDS_EN + _OVERDUE_KEYWORDS_RU):
        return True
    return False


_MOST_IMPORTANT_KEYWORDS_EN = (
    "what's most important", "what is most important",
    "what's the most important", "what is the most important",
    "which task is most important", "which task should i work on",
    "what should i work on", "what's urgent", "what is urgent",
)
_MOST_IMPORTANT_KEYWORDS_RU = (
    "что самое главное",
    "что у меня сейчас самое главное",
    "что для меня сейчас самое главное",
    "что для меня самое главное",
    "какая задача самая важная",
    "какая сейчас самая важная задача",
    "что самое важное",
    "что для меня самое важное",
    "самый важный",
    "самое важное",
    "самый приоритетн",
    "самое приоритетн",
)



def _is_today_query(message: str) -> bool:
    """Detect read-only queries asking specifically about today's tasks."""
    low = message.lower().strip()
    keywords = (
        "что нужно сделать сегодня",
        "что делать сегодня",
        "задачи на сегодня",
        "что у меня сегодня",
        "что надо сделать сегодня",
        "какие задачи сегодня",
        "что сегодня нужно сделать",
        "what do i need to do today",
        "what should i do today",
        "what tasks are due today",
        "tasks for today",
    )
    return any(kw in low for kw in keywords)

def _is_most_important_query(message: str) -> bool:
    """Detect queries asking for the single most important task."""
    low = message.lower().strip()
    return any(kw in low for kw in _MOST_IMPORTANT_KEYWORDS_EN + _MOST_IMPORTANT_KEYWORDS_RU)


_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


def _select_most_important(tasks: list[dict]) -> tuple[dict, str]:
    """Deterministically pick the single most important task from a list.

    Rules:
      1. Higher priority tier wins: urgent > high > medium > low.
      2. Among equal priority, the task with the earliest deadline wins
         (tasks without a deadline are pushed to the back).
      3. Final tiebreaker: most recently created task wins.

    Returns (task_dict, reason_string).
    """
    def _sort_key(t: dict) -> tuple[int, str, str]:
        priority_rank = _PRIORITY_ORDER.get(t.get("priority", "low"), 99)
        deadline = t.get("deadline") or "9999-12-31"
        created = t.get("id", "")  # UUID v4 — lexicographic ≈ recent
        return (priority_rank, deadline, created)

    best = min(tasks, key=_sort_key)
    reason = f"приоритет {best['priority']}"
    if best.get("deadline"):
        reason += f", дедлайн {best['deadline']}"
    return best, reason


_COMPLETE_TASK_PATTERNS_RU = (
    r"отметь\s+(?:задачу\s+)?[«\"']?(.+?)[»\"']?\s+(?:как\s+)?выполненн",
    r"заверши\s+(?:задачу\s+)?[«\"']?(.+?)[»\"']?$",
    r"выполни\s+(?:задачу\s+)?[«\"']?(.+?)[»\"']?$",
    r"задача\s+[«\"']?(.+?)[»\"']?\s+выполнена",
    r"задачу\s+[«\"']?(.+?)[»\"']?\s+(?:как\s+)?выполненн",
)
_COMPLETE_TASK_PATTERNS_EN = (
    r"(?:mark|mark\s+the)\s+(?:task\s+)?[\"'](.+?)[\"']\s+(?:as\s+)?(?:done|completed|complete|finished)",
    r"(?:complete|finish|done\s+with)\s+(?:the\s+)?(?:task\s+)?[\"'](.+?)[\"']",
    r"(?:complete|finish|done\s+with)\s+(?:the\s+)?task\s+(.+)",
    r"task\s+[\"'](.+?)[\"']\s+(?:is\s+)?(?:done|completed|complete|finished)",
)

_COMPLETE_TASK_VERBS_EN = (
    "complete ", "finish ", "done with ", "mark done ", "mark as done ",
    "mark complete ", "mark as complete ",
)
_COMPLETE_TASK_VERBS_RU = (
    "отметь", "заверши", "выполни",
)


def _parse_complete_task_title(message: str) -> str | None:
    """Extract the task title from a complete-task command message.

    Tries regex patterns first (handles quoted and bracketed titles),
    then falls back to a simple verb + remainder extraction.
    Returns the cleaned title string, or None if the message is not a
    recognized complete-task command.
    """
    low = message.lower().strip()
    for pattern in _COMPLETE_TASK_PATTERNS_RU + _COMPLETE_TASK_PATTERNS_EN:
        m = re.search(pattern, low)
        if m:
            title = m.group(1).strip()
            title = re.sub(r"^[«\"'\s]+|[»\"'\s]+$", "", title)
            if title:
                return title

    for verb in _COMPLETE_TASK_VERBS_EN:
        if low.startswith(verb):
            title = message[len(verb):].strip()
            title = re.sub(r"^(the|a|task)\s+", "", title, flags=re.IGNORECASE)
            title = re.sub(r"^[\"']|[\"']$", "", title).strip()
            if title:
                return title

    for verb in _COMPLETE_TASK_VERBS_RU:
        if low.startswith(verb):
            remainder = message[len(verb):].strip()
            remainder = re.sub(r"^(задачу|задача|задачи|the|a)\s+", "", remainder, flags=re.IGNORECASE)
            remainder = re.sub(r"^[«\"'\s]+|[»\"'\s]+$", "", remainder).strip()
            if remainder:
                return remainder

    return None



def _parse_create_task_title(message: str) -> str | None:
    """Extract a task title from an explicit create-task request."""

    text = message.strip()

    prefixes = [
        "создай новую задачу:",
        "создай задачу:",
        "создать новую задачу:",
        "создать задачу:",
        "добавь новую задачу:",
        "добавь задачу:",
    ]

    lower = text.lower()

    for prefix in prefixes:
        if lower.startswith(prefix):
            title = text[len(prefix):].strip()

            # Remove optional surrounding quotes.
            if len(title) >= 2 and title[0] in "\"«'" and title[-1] in "\"»'":
                title = title[1:-1].strip()

            # Remove trailing explanation after the title only when
            # it is clearly a separate sentence.
            if ". Оцени" in title:
                title = title.split(". Оцени", 1)[0].strip()

            if title:
                return title

    return None


async def _try_create_task_from_message(
    message: str,
    ctx,
    db,
    context,
):
    title = _parse_create_task_title(message)

    if not title:
        return None

    # Import here to avoid changing the existing import structure.
    from app.ai.tools import execute_tool

    # IMPORTANT:
    # Do NOT pass priority here.
    # execute_tool() will call score_priority() automatically.
    outcome = await execute_tool(
        db,
        ctx.workspace_id,
        ctx.user.id,
        "create_task",
        {
            "title": title,
        },
    )

    priority = outcome.get("priority", "medium")
    reason = outcome.get("priority_reason")

    reply = f"Задача «{title}» создана.\nПриоритет: {priority}."

    if reason:
        reply += f"\nПочему: {reason}."

    return reply, [outcome]


async def _try_complete_task(
    message: str,
    ctx: WorkspaceContext,
    db: AsyncSession,
    context: dict,
) -> tuple[str, list[dict]] | None:
    """Deterministically handle a complete-task command without needing LLM.

    Uses the task list from the pre-built context (which already respects
    workspace isolation) to find a match, then updates the DB directly.

    Returns (reply_text, actions_taken) on success, or None if the message
    is not a recognized complete-task command.
    """
    title = _parse_complete_task_title(message)
    if not title:
        return None

    active_tasks = context.get("all_active_tasks", [])
    if not active_tasks:
        return (f"У вас нет активных задач с названием «{title}».", [])

    title_lower = title.lower()
    matches = [t for t in active_tasks if title_lower in t["title"].lower()]

    if not matches:
        return (f"Задача «{title}» не найдена среди активных задач.", [])

    if len(matches) > 1:
        titles = ", ".join(f"«{t['title']}»" for t in matches)
        return (
            f"Найдено несколько задач, подходящих под «{title}»: {titles}. "
            "Пожалуйста, уточните, какую именно задачу нужно завершить.",
            [],
        )

    task_dict = matches[0]
    task_id = task_dict["id"]

    task = (await db.execute(
        select(Task).where(Task.workspace_id == ctx.workspace_id, Task.id == task_id)
    )).scalars().first()

    if task is None:
        return (f"Задача «{title}» не найдена.", [])

    if task.status == TaskStatus.done:
        return (f"Задача «{task.title}» уже завершена.", [])

    task.status = TaskStatus.done
    task.completed_at = datetime.now(timezone.utc)
    await db.commit()

    db.add(ChatMessage(
        workspace_id=ctx.workspace_id, user_id=ctx.user.id,
        role=ChatRole.assistant, content=f"Задача «{task.title}» отмечена как выполненная.",
    ))
    await db.commit()

    return (
        f"Задача «{task.title}» отмечена как выполненная.",
        [{"type": "task_completed", "id": str(task.id), "title": task.title}],
    )


router = APIRouter(prefix="/assistant", tags=["assistant"])

_SYSTEM_PROMPT = """You are Operator AI, an AI Chief of Staff.

=== CURRENT DATA ===
The "Current workspace context" JSON below contains the user's real active tasks, \
commitments, and waiting-for items. Use this data to answer ALL questions about \
the user's tasks, priorities, deadlines, and status. Do NOT call any tools to \
retrieve information — the data is already provided.

IMPORTANT: The key "all_active_tasks" contains EVERY open task (status=todo or \
in_progress) for this workspace, sorted by priority_score descending. Use this \
list when the user asks "what tasks do I have?", "какие задачи?", or any \
similar question. Never invent or guess task names — only reference tasks that \
appear in all_active_tasks.

=== WHEN TO USE TOOLS (ONLY these cases) ===
- User asks to CREATE a new task/commitment/waiting-for → use create_task, \
create_commitment, or create_waiting_for.
- User asks to COMPLETE/MARK DONE/DELETE/CANCEL an existing item → respond with \
text explaining what would change; do NOT call any tool for destructive actions.

=== WHEN NOT TO USE TOOLS ===
- "What tasks do I have?" / "Какие задачи?" / "Show my tasks" → answer from \
all_active_tasks in context.
- "What's most important?" / "Что самое главное?" → find the highest-priority \
task in all_active_tasks, explain why, do NOT call tools.
- Any read-only question → answer from context, do NOT call tools.

=== RULES ===
1. NEVER call create_task (or any tool) in response to a question about existing data.
2. When listing tasks, include: title, priority, status, deadline (if set).
3. When asked "what is most important", pick the task with the highest priority \
(or highest priority_score) and explain why.
4. Keep responses concise and in the user's language.
5. Only confirm tool usage with "Done — ..." when you actually created something."""


@router.get("/history")
async def get_history(ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ChatMessage).where(ChatMessage.workspace_id == ctx.workspace_id, ChatMessage.user_id == ctx.user.id)
        .order_by(ChatMessage.created_at.asc()).limit(200)
    )).scalars().all()
    return [{"role": m.role.value, "content": m.content} for m in rows]


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, ctx: WorkspaceContext = Depends(get_workspace_context), db: AsyncSession = Depends(get_db)):
    db.add(ChatMessage(workspace_id=ctx.workspace_id, user_id=ctx.user.id, role=ChatRole.user, content=payload.message))
    await db.commit()

    history_rows = (await db.execute(
        select(ChatMessage).where(ChatMessage.workspace_id == ctx.workspace_id, ChatMessage.user_id == ctx.user.id)
        .order_by(ChatMessage.created_at.asc()).limit(20)
    )).scalars().all()
    messages = [{"role": m.role.value, "content": m.content} for m in history_rows]

    context = await build_context(db, ctx.workspace_id, ctx.user.id)

    complete_result = await _try_complete_task(payload.message, ctx, db, context)
    if complete_result is not None:
        reply, actions = complete_result
        return ChatResponse(reply=reply, actions_taken=actions)

    create_result = await _try_create_task_from_message(
        payload.message, ctx, db, context
    )
    if create_result is not None:
        reply, actions = create_result
        return ChatResponse(reply=reply, actions_taken=actions)

    read_only = _is_read_only_query(payload.message)

    if read_only and context.get("all_active_tasks"):
        tasks = context["all_active_tasks"]

        if _is_overdue_query(payload.message):
            today = date.today()
            overdue = [
                t for t in tasks
                if (
                    t.get("deadline")
                    and t["deadline"] < today.isoformat()
                    and t.get("status") in ("todo", "in_progress")
                )
            ]
            if overdue:
                lines = []
                for t in overdue:
                    parts = [f"• {t['title']}"]
                    parts.append(f"приоритет: {t['priority']}")
                    parts.append(f"дедлайн: {t['deadline']}")
                    lines.append(", ".join(parts))
                word = "задача" if len(overdue) == 1 else "задачи" if len(overdue) < 5 else "задач"
                reply = f"Просрочено {len(overdue)} {word}:\n" + "\n".join(lines)
            else:
                reply = "Просроченных задач сейчас нет."

        elif _is_most_important_query(payload.message):
            best, reason = _select_most_important(tasks)
            reply = f"Самая важная задача сейчас: «{best['title']}» — {reason}."
            if best.get("deadline"):
                reply += f" Дедлайн: {best['deadline']}."
        else:
            lines = []
            for t in tasks:
                parts = [f"• {t['title']}"]
                parts.append(f"приоритет: {t['priority']}")
                if t.get("deadline"):
                    parts.append(f"дедлайн: {t['deadline']}")
                lines.append(", ".join(parts))
            reply = f"Сейчас у вас {len(tasks)} активных задач:\n" + "\n".join(lines)

        db.add(ChatMessage(workspace_id=ctx.workspace_id, user_id=ctx.user.id, role=ChatRole.assistant, content=reply))
        await db.commit()
        return ChatResponse(reply=reply, actions_taken=[])

    system_prompt = _SYSTEM_PROMPT + f"\n\nCurrent workspace context (JSON): {context}"

    provider = get_ai_provider()
    result = await provider.chat(system_prompt, messages, tools=TOOL_SCHEMAS)

    actions_taken = []
    if not read_only:
        for call in result.get("tool_calls", []):
            try:
                outcome = await execute_tool(db, ctx.workspace_id, ctx.user.id, call["name"], call["arguments"])
                actions_taken.append(outcome)
            except (ValueError, KeyError) as e:
                actions_taken.append({"error": str(e), "tool": call.get("name")})

    reply = result.get("content") or (
        f"Done — {', '.join(a.get('title', a.get('tool', '')) for a in actions_taken)}."
        if actions_taken else
        "Не удалось получить текстовый ответ от AI-провайдера. Проверьте подключение Ollama."
    )
    db.add(ChatMessage(workspace_id=ctx.workspace_id, user_id=ctx.user.id, role=ChatRole.assistant, content=reply))
    await db.commit()

    return ChatResponse(reply=reply, actions_taken=actions_taken)
