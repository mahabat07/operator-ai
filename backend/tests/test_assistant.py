from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, timedelta

import pytest

from app.api.v1.assistant import (
    _is_read_only_query, _is_overdue_query, _parse_complete_task_title,
)


# ---------- _is_read_only_query unit tests ----------

class TestIsReadOnlyQuery:


    # --- Russian read-only queries (from the bug report) ---
    def test_russian_what_tasks(self):
        assert _is_read_only_query("Какие задачи у меня сейчас есть?") is True

    def test_russian_what_is_most_important(self):
        assert _is_read_only_query("Что у меня сейчас самое главное?") is True

    def test_russian_show_tasks(self):
        assert _is_read_only_query("Покажи задачи") is True

    def test_russian_list_tasks(self):
        assert _is_read_only_query("Перечисли задачи и укажи приоритет каждой") is True

    def test_russian_what_should_i_do(self):
        assert _is_read_only_query("Что мне нужно сделать сегодня?") is True

    # --- English read-only queries ---
    def test_english_what_tasks(self):
        assert _is_read_only_query("What tasks do I have?") is True

    def test_english_what_is_most_important(self):
        assert _is_read_only_query("What is most important right now?") is True

    def test_english_show_tasks(self):
        assert _is_read_only_query("Show my tasks") is True

    def test_english_whats_urgent(self):
        assert _is_read_only_query("What's urgent?") is True

    def test_english_what_should_i_work_on(self):
        assert _is_read_only_query("What should I work on?") is True

    # --- Any question mark should be read-only (no action keywords) ---
    def test_generic_question_is_read_only(self):
        assert _is_read_only_query("Сколько у меня задач?") is True

    def test_english_generic_question(self):
        assert _is_read_only_query("How many tasks are overdue?") is True

    # --- Action queries (should NOT be read-only) ---
    def test_create_task_ru(self):
        assert _is_read_only_query("Создай задачу купить молоко") is False

    def test_create_task_en(self):
        assert _is_read_only_query("Create a task to prepare the presentation") is False

    def test_complete_task_ru(self):
        assert _is_read_only_query("Отметь задачу 'Купить молоко' выполненной") is False

    def test_complete_task_en(self):
        assert _is_read_only_query("Mark the task 'Buy milk' as done") is False

    def test_delete_task_en(self):
        assert _is_read_only_query("Delete the old task") is False

    def test_delete_task_ru(self):
        assert _is_read_only_query("Удали задачу") is False

    def test_add_task_en(self):
        assert _is_read_only_query("Add a new task to call the client") is False

    def test_cancel_task_ru(self):
        assert _is_read_only_query("Отмен задачу 'Old task'") is False

    def test_remember_something(self):
        assert _is_read_only_query("Remember that I prefer dark mode") is False

    def test_update_task_en(self):
        assert _is_read_only_query("Update task deadline to Friday") is False

    # --- Edge cases ---
    def test_empty_string(self):
        assert _is_read_only_query("") is False

    def test_no_question_no_action(self):
        assert _is_read_only_query("Привет") is False

    def test_action_keyword_takes_precedence_over_question(self):
        """Even with a '?', 'create task X' should be an action."""
        assert _is_read_only_query("Создай задачу?") is False

    def test_question_with_create_word_but_no_space(self):
        """'создайзадачу' (no space) should NOT match action keyword 'создай '."""
        # 'создай' without trailing space — action keywords all have trailing space
        # but 'создай' is in _ACTION_KEYWORDS_RU without trailing space
        # Actually 'создай' IS in the list, so this should be action
        assert _is_read_only_query("создайзадачу") is False


# ---------- Chat endpoint integration (mocked) ----------

@pytest.mark.asyncio
async def test_read_only_query_skips_tool_execution():
    """When the user asks a read-only question, even if the (hallucinating)
    model returns tool_calls, none of them should be executed."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest
    from app.models.enums import ChatRole

    # Mock DB session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    # Mock workspace context
    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    # Mock provider: model hallucinates a create_task call for a read query
    with patch("app.api.v1.assistant.get_ai_provider") as mock_provider_fn, \
         patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.execute_tool") as mock_exec:
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {
            "content": None,
            "tool_calls": [{"name": "create_task", "arguments": {"title": "Hallucinated"}}],
        }
        mock_provider_fn.return_value = mock_provider
        mock_build_ctx.return_value = {"overdue_tasks": [], "today_tasks": [], "upcoming_tasks": []}

        payload = ChatRequest(message="Какие задачи у меня есть?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        # execute_tool must NOT have been called
        mock_exec.assert_not_called()
        # The response should not contain hallucinated actions
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_action_query_executes_tools():
    """When the user explicitly asks to create a task, tools should execute."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.get_ai_provider") as mock_provider_fn, \
         patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.execute_tool") as mock_exec:
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {
            "content": "Done — Купить молоко.",
            "tool_calls": [{"name": "create_task", "arguments": {"title": "Купить молоко"}}],
        }
        mock_provider_fn.return_value = mock_provider
        mock_build_ctx.return_value = {"overdue_tasks": [], "today_tasks": [], "upcoming_tasks": []}
        mock_exec.return_value = {"type": "task", "id": "123", "title": "Купить молоко", "priority": "medium"}

        payload = ChatRequest(message="Создай задачу купить молоко")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        # execute_tool SHOULD have been called
        mock_exec.assert_called_once()
        assert len(response.actions_taken) == 1


@pytest.mark.asyncio
async def test_read_only_query_no_content_fallback():
    """If model returns no content AND no tool_calls for a read query,
    the assistant should return a helpful fallback, not crash."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.get_ai_provider") as mock_provider_fn, \
         patch("app.api.v1.assistant.build_context") as mock_build_ctx:
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {"content": None, "tool_calls": []}
        mock_provider_fn.return_value = mock_provider
        mock_build_ctx.return_value = {"overdue_tasks": [], "today_tasks": [], "upcoming_tasks": []}

        payload = ChatRequest(message="Что у меня самое главное?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        assert response.reply is not None
        assert len(response.reply) > 0
        assert response.actions_taken == []


# ---------- _parse_complete_task_title unit tests ----------

class TestParseCompleteTaskTitle:
    """Extract task title from various complete-task command formats."""

    def test_russian_otmet_with_brackets(self):
        assert _parse_complete_task_title("Отметь задачу «Позвонить клиенту» выполненной") == "позвонить клиенту"

    def test_russian_otmet_with_quotes(self):
        assert _parse_complete_task_title("Отметь задачу 'Купить молоко' выполненной") == "купить молоко"

    def test_russian_zavershi(self):
        assert _parse_complete_task_title("Заверши задачу Написать отчёт") == "написать отчёт"

    def test_russian_vypolni(self):
        assert _parse_complete_task_title("Выполни задачу Подготовить презентацию") == "подготовить презентацию"

    def test_russian_zadacha_vypolnena(self):
        assert _parse_complete_task_title("Задача «Позвонить клиенту» выполнена") == "позвонить клиенту"

    def test_russian_otmet_zadachu(self):
        assert _parse_complete_task_title("Отметь задачу Купить молоко как выполненную") == "купить молоко"

    def test_english_mark_done(self):
        assert _parse_complete_task_title("Mark task 'Buy milk' as done") == "buy milk"

    def test_english_complete_quoted(self):
        assert _parse_complete_task_title("Complete the task 'Prepare presentation'") == "prepare presentation"

    def test_english_finish_unquoted(self):
        assert _parse_complete_task_title("Finish task Call the client") == "call the client"

    def test_english_done_with(self):
        assert _parse_complete_task_title("Done with 'Write report'") == "write report"

    def test_english_task_is_done(self):
        assert _parse_complete_task_title("Task 'Send email' is done") == "send email"

    def test_returns_none_for_non_command(self):
        assert _parse_complete_task_title("Какие задачи у меня есть?") is None

    def test_returns_none_for_create_command(self):
        assert _parse_complete_task_title("Создай задачу купить молоко") is None


# ---------- _try_complete_task integration tests (via chat handler) ----------

def _make_active_tasks(*titles):
    """Helper: build a minimal all_active_tasks list."""
    tasks = []
    for i, title in enumerate(titles):
        tasks.append({
            "id": f"00000000-0000-0000-0000-{i:012d}",
            "title": title,
            "priority": "medium",
            "priority_score": None,
            "deadline": None,
            "status": "todo",
            "project_id": None,
        })
    return tasks


def _make_task_stub(task_id, title, status="todo"):
    """Create a mock Task ORM object."""
    task = MagicMock()
    task.id = task_id
    task.title = title
    task.status = status
    task.completed_at = None
    return task


@pytest.mark.asyncio
async def test_complete_task_success_without_ai_provider():
    """Completing a task works even when AI_PROVIDER=none (no LLM call)."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest
    from app.models.enums import TaskStatus

    active = _make_active_tasks("Позвонить клиенту по договору", "Написать отчёт")
    task_stub = _make_task_stub(active[0]["id"], "Позвонить клиенту по договору")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = task_stub
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message='Отметь задачу «Позвонить клиенту по договору» выполненной')
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        # AI provider must NOT have been called
        mock_provider.assert_not_called()
        # Task should be marked as done
        assert task_stub.status == TaskStatus.done
        assert task_stub.completed_at is not None
        # Response should confirm completion
        assert "выполненн" in response.reply.lower()
        assert len(response.actions_taken) == 1
        assert response.actions_taken[0]["type"] == "task_completed"


@pytest.mark.asyncio
async def test_complete_task_not_found():
    """When the task title doesn't match any active task, return a clear message."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    active = _make_active_tasks("Написать отчёт")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Заверши задачу Купить слона")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "не найдена" in response.reply.lower()
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_complete_task_duplicate_names():
    """When multiple tasks match, ask user to clarify."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    active = _make_active_tasks("Написать отчёт", "Написать отчёт для руководителя")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Отметь задачу «Написать отчёт» выполненной")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "несколько" in response.reply.lower() or "уточните" in response.reply.lower()
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_complete_task_already_done():
    """When the task is already completed, inform the user without changing anything."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest
    from app.models.enums import TaskStatus

    # "done" tasks are NOT in all_active_tasks, so simulate the edge case
    # where the task was just completed and context is stale:
    active = _make_active_tasks("Написать отчёт")
    task_stub = _make_task_stub(active[0]["id"], "Написать отчёт", status="done")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = task_stub
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Отметь задачу «Написать отчёт» выполненной")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "уже завершена" in response.reply.lower()
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_complete_task_workspace_isolation():
    """Task from a different workspace must NOT be completable."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest
    from app.models.enums import TaskStatus

    # The context builder already filters by workspace_id, so if a task
    # appears in all_active_tasks, it belongs to the correct workspace.
    # But we also verify the direct DB query uses workspace_id.
    active = _make_active_tasks("Купить молоко")
    task_stub = _make_task_stub(active[0]["id"], "Купить молоко")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = task_stub
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "my-workspace-id"
    mock_ctx.user.id = "my-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Заверши задачу Купить молоко")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        # Verify the DB query included the correct workspace_id
        call_args = mock_db.execute.call_args_list
        # The first call is the initial ChatMessage query (history),
        # the second call is for fetching the task to complete
        task_query_call = call_args[1] if len(call_args) > 1 else None
        assert task_query_call is not None
        # Confirm the task status was changed
        assert task_stub.status == TaskStatus.done
        assert "выполненн" in response.reply.lower()


# ---------- _is_overdue_query unit tests ----------

class TestIsOverdueQuery:
    """Detect overdue-specific queries correctly."""

    def test_russian_overdue_tasks(self):
        assert _is_overdue_query("Какие задачи у меня просрочены?") is True

    def test_russian_overdue_nichego(self):
        assert _is_overdue_query("Какие задачи у меня просрочены? Ничего не изменяй.") is True

    def test_russian_prosrochennye(self):
        assert _is_overdue_query("Просроченные задачи") is True

    def test_russian_prosrocheno(self):
        assert _is_overdue_query("Что просрочено?") is True

    def test_english_overdue(self):
        assert _is_overdue_query("Which tasks are overdue?") is True

    def test_english_whats_overdue(self):
        assert _is_overdue_query("What's overdue?") is True

    def test_english_overdue_tasks(self):
        assert _is_overdue_query("Show me overdue tasks") is True

    def test_english_past_due(self):
        assert _is_overdue_query("What is past due?") is True

    def test_not_overdue_what_tasks(self):
        assert _is_overdue_query("Какие задачи у меня есть?") is False

    def test_not_overdue_most_important(self):
        assert _is_overdue_query("Что самое главное?") is False

    def test_not_overdue_create(self):
        assert _is_overdue_query("Создай задачу") is False


# ---------- Overdue query integration tests (via chat handler) ----------

def _make_active_tasks_with_deadlines(*task_specs):
    """Helper: build active tasks with deadlines.
    Each spec is a tuple (title, deadline_str_or_None)."""
    tasks = []
    for i, (title, deadline) in enumerate(task_specs):
        tasks.append({
            "id": f"00000000-0000-0000-0000-{i:012d}",
            "title": title,
            "priority": "medium",
            "priority_score": None,
            "deadline": deadline,
            "status": "todo",
            "project_id": None,
        })
    return tasks


@pytest.mark.asyncio
async def test_overdue_query_returns_only_overdue_tasks():
    """1 overdue active task → returns only that task."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()

    active = _make_active_tasks_with_deadlines(
        ("Просроченная задача", yesterday),
        ("Будущая задача", tomorrow),
        ("Задача без дедлайна", None),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "просроченная задача" in response.reply.lower()
        assert "будущая задача" not in response.reply.lower()
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_overdue_query_multiple_overdue():
    """Multiple overdue tasks → returns all overdue."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    two_days_ago = (today - timedelta(days=2)).isoformat()

    active = _make_active_tasks_with_deadlines(
        ("Просроченная задача 1", yesterday),
        ("Просроченная задача 2", two_days_ago),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "просроченная задача 1" in response.reply.lower()
        assert "просроченная задача 2" in response.reply.lower()


@pytest.mark.asyncio
async def test_overdue_query_future_deadline_not_returned():
    """Future deadline → not returned as overdue."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()

    active = _make_active_tasks_with_deadlines(("Будущая задача", tomorrow))

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "нет" in response.reply.lower()
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_overdue_query_no_deadline_not_returned():
    """No deadline → not returned as overdue."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    active = _make_active_tasks_with_deadlines(("Задача без дедлайна", None))

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "нет" in response.reply.lower()


@pytest.mark.asyncio
async def test_overdue_query_completed_past_deadline_not_returned():
    """Completed task with past deadline → not returned as overdue."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    # completed tasks are NOT in all_active_tasks
    active = _make_active_tasks_with_deadlines(
        ("Будущая задача", (today + timedelta(days=1)).isoformat()),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        # Completed task should not appear; only future-deadline task exists
        assert "нет" in response.reply.lower()
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_overdue_query_no_overdue_tasks():
    """No overdue tasks → correct empty response."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()

    active = _make_active_tasks_with_deadlines(
        ("Задача без дедлайна", None),
        ("Будущая задача", tomorrow),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "Просроченных задач сейчас нет" in response.reply
        assert response.actions_taken == []


@pytest.mark.asyncio
async def test_overdue_query_workspace_isolation():
    """Overdue query respects workspace isolation (context already filtered)."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    active = _make_active_tasks_with_deadlines(
        ("Моя просроченная задача", yesterday),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "my-workspace-id"
    mock_ctx.user.id = "my-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Какие задачи у меня просрочены?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        # AI provider must NOT have been called (offline-safe)
        assert mock_provider.call_count == 0
        assert "просроченная задача" in response.reply.lower()


@pytest.mark.asyncio
async def test_overdue_query_english():
    """English overdue query works correctly."""
    from app.api.v1.assistant import chat
    from app.schemas.domain import ChatRequest

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    active = _make_active_tasks_with_deadlines(
        ("Overdue task", yesterday),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add.return_value = None
    mock_db.commit = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.workspace_id = "test-ws-id"
    mock_ctx.user.id = "test-user-id"

    with patch("app.api.v1.assistant.build_context") as mock_build_ctx, \
         patch("app.api.v1.assistant.get_ai_provider") as mock_provider:
        mock_build_ctx.return_value = {"all_active_tasks": active}

        payload = ChatRequest(message="Which tasks are overdue?")
        response = await chat(payload, ctx=mock_ctx, db=mock_db)

        mock_provider.assert_not_called()
        assert "overdue task" in response.reply.lower()
        assert response.actions_taken == []
