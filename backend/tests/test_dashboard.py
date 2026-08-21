from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_db(count_results):
    db = AsyncMock()
    call_count = [0]

    async def mock_execute(query):
        result = MagicMock()
        index = call_count[0]
        call_count[0] += 1

        if index < len(count_results):
            result.scalar_one.return_value = count_results[index]
        else:
            result.scalars.return_value.all.return_value = []

        return result

    db.execute = mock_execute
    return db


def make_context():
    ctx = MagicMock()
    ctx.workspace_id = "test-ws-id"
    ctx.user.id = "test-user-id"
    return ctx


def make_provider(response=None):
    provider = MagicMock()
    provider.complete_json = AsyncMock(return_value=response or {})
    return provider


@pytest.mark.asyncio
async def test_dashboard_works_without_ai_provider():
    """Dashboard returns metrics even when AI returns empty."""
    from app.api.v1.dashboard import get_dashboard

    db = make_db([7, 1, 0, 0, 1, 0, 0, 0])
    ctx = make_context()
    provider = make_provider()

    with patch(
        "app.api.v1.dashboard.get_ai_provider",
        return_value=provider,
    ):
        response = await get_dashboard(ctx=ctx, db=db)

    assert "metrics" in response
    assert "ai_briefing" in response
    assert response["metrics"]["open_tasks"] == 7
    assert response["metrics"]["completed_today"] == 1


@pytest.mark.asyncio
async def test_dashboard_fallback_briefing_without_ai():
    """Empty AI response produces fallback briefing."""
    from app.api.v1.dashboard import get_dashboard

    db = make_db([0, 0, 0, 0, 0, 0, 0, 0])
    ctx = make_context()
    provider = make_provider()

    with patch(
        "app.api.v1.dashboard.get_ai_provider",
        return_value=provider,
    ):
        response = await get_dashboard(ctx=ctx, db=db)

    assert response["ai_briefing"]
    assert "Connect an AI provider" not in response["ai_briefing"]


@pytest.mark.asyncio
async def test_dashboard_overdue_excludes_completed():
    """Completed tasks are not counted as overdue."""
    from app.api.v1.dashboard import get_dashboard

    db = make_db([5, 0, 0, 0, 2, 0, 0, 0])
    ctx = make_context()
    provider = make_provider()

    with patch(
        "app.api.v1.dashboard.get_ai_provider",
        return_value=provider,
    ):
        response = await get_dashboard(ctx=ctx, db=db)

    assert response["metrics"]["overdue"] == 0


@pytest.mark.asyncio
async def test_dashboard_metrics_are_independent_of_ai_provider():
    """Dashboard metrics come from DB, not AI."""
    from app.api.v1.dashboard import get_dashboard

    db = make_db([3, 2, 1, 1, 4, 2, 1, 1])
    ctx = make_context()
    provider = make_provider()

    with patch(
        "app.api.v1.dashboard.get_ai_provider",
        return_value=provider,
    ):
        response = await get_dashboard(ctx=ctx, db=db)

    assert response["metrics"]["open_tasks"] == 3
    assert response["metrics"]["completed_today"] == 2
    assert response["metrics"]["overdue"] == 1
    assert response["metrics"]["active_projects"] == 1
    assert response["metrics"]["upcoming_deadlines"] == 4
    assert response["metrics"]["open_commitments"] == 2
    assert response["metrics"]["waiting_for"] == 1
    assert response["metrics"]["risks"] == 1


@pytest.mark.asyncio
async def test_dashboard_displays_ai_morning_brief():
    """Dashboard displays AI morning brief when provider returns one."""
    from app.api.v1.dashboard import get_dashboard

    db = make_db([1, 0, 0, 0, 0, 0, 0, 0])
    ctx = make_context()

    provider = make_provider(
        {
            "morning_brief": "Сейчас главное — исправить критическую задачу."
        }
    )

    with patch(
        "app.api.v1.dashboard.get_ai_provider",
        return_value=provider,
    ):
        response = await get_dashboard(ctx=ctx, db=db)

    assert (
        response["ai_briefing"]
        == "Сейчас главное — исправить критическую задачу."
    )
