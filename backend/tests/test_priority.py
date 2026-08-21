from datetime import date, timedelta

from app.ai.prioritizer import _heuristic_score
from app.models.enums import Priority


def test_urgent_language_scores_high():
    result = _heuristic_score("URGENT: fix production outage", None, None, date.today(), None, 0)
    assert result["priority"] in (Priority.high, Priority.urgent)
    assert result["score"] > 50


def test_overdue_deadline_boosts_score():
    yesterday = date.today() - timedelta(days=1)
    result = _heuristic_score("Send report", None, yesterday, date.today(), None, 0)
    assert "deadline has passed" in result["reason"]
    assert result["score"] >= 55


def test_plain_task_is_not_forced_to_medium():
    result = _heuristic_score("Water the office plants", None, None, date.today(), None, 0)
    assert result["priority"] == Priority.low


def test_business_critical_project_raises_score():
    low = _heuristic_score("Update internal wiki page", None, None, date.today(), None, 0)
    high = _heuristic_score("Update internal wiki page", None, None, date.today(), "critical", 0)
    assert high["score"] > low["score"]
