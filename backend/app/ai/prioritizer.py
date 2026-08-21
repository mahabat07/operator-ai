from datetime import date
from typing import Any, Optional

from app.ai.provider import AIProvider
from app.models.enums import Priority, PrioritySource

_URGENT_WORDS = (
    "urgent", "asap", "critical", "immediately", "down", "outage", "breach",
    "users can", "block",
    "user can", "users cannot",
    "blocked", "prevent",
    "срочно", "немедленно", "критичн", "горит", "упал", "недоступен",
    "авария", "сбой", "проблема", "блокирует", "_Block",
)
_HIGH_WORDS = (
    "important", "deadline", "client", "contract", "investor", "revenue",
    "security", "production", "error", "bug", "payment", "invoice",
    "brought", "key", "major", "serious",
    "важн", "клиент", "контракт", "дедлайн", "инвестор", "деньги",
    "безопасност", "продукш", "ошибк", "оплат", "счёт",
    "отчёт", "к пятнице", "к завтра",
)
_MEDIUM_WORDS = (
    "feature", "button", "endpoint", "dashboard", "report", "update",
    "add", "create", "build", "implement", "prepare",
    "кнопк", "эндпоинт",
    "подготовить", "добавить", "создать", "реализовать",
)
_LOW_WORDS = (
    "when", "time", "nice", "optional", "cosmetic", "someday",
    "maybe", "if possible", "readme",
    "когда", "время", "можно", "позже", "когда-нибудь",
)

_SYSTEM_PROMPT = """You are the prioritization engine inside an AI Chief-of-Staff product.
Given a task/commitment (title, description, deadline, project business impact,
number of tasks that depend on it), decide how important and urgent it is.

Return ONLY a JSON object:
{
  "priority": "low" | "medium" | "high" | "urgent",
  "score": <integer 0-100>,
  "reason": "<one short sentence explaining why, in the same language as the input>"
}

Weigh, in order: (1) explicit urgency/importance language in the text,
(2) deadline proximity, (3) business impact of the related project,
(4) how many other tasks are blocked waiting on this one.
"""


def _heuristic_score(
    title: str, description: str | None, deadline: Optional[date], today: date,
    business_impact: str | None, blocking_count: int,
) -> dict[str, Any]:
    """Deterministic fallback when no LLM is configured. Runs unconditionally
    so Priorities/Tasks are never silently stuck at 'medium' even without an
    API key - it just won't be as nuanced as the LLM path."""
    text = f"{title} {description or ''}".lower()
    score = 20
    reasons = []


    if any(w in text for w in _URGENT_WORDS):
        score += 55
        reasons.append("urgency language detected")
    elif any(w in text for w in _HIGH_WORDS):
        score += 30
        reasons.append("high-importance language detected")
    elif any(w in text for w in _LOW_WORDS):
        score -= 10
        reasons.append("optional/non-urgent language detected")
    elif any(w in text for w in _MEDIUM_WORDS):
        score += 5
        reasons.append("standard work language detected")

    #
    if deadline:
        days_left = (deadline - today).days
        if days_left < 0:
            score += 35
            reasons.append("deadline has passed")
        elif days_left == 0:
            score += 30
            reasons.append("due today")
        elif days_left <= 2:
            score += 20
            reasons.append("due within 2 days")
        elif days_left <= 7:
            score += 8
            reasons.append("due this week")


    impact_weight = {"critical": 20, "high": 14, "medium": 6, "low": 0}
    if business_impact:
        score += impact_weight.get(business_impact, 0)
        if business_impact in ("critical", "high"):
            reasons.append(f"{business_impact} business impact project")


    if blocking_count > 0:
        score += min(blocking_count * 8, 20)
        reasons.append(f"blocks {blocking_count} other task(s)")

    score = max(0, min(100, score))
    if score >= 75:
        priority = Priority.urgent
    elif score >= 50:
        priority = Priority.high
    elif score >= 25:
        priority = Priority.medium
    else:
        priority = Priority.low

    return {
        "priority": priority,
        "score": score,
        "reason": "; ".join(reasons) or "no strong urgency/importance signal found",
        "source": PrioritySource.default,
    }


async def score_priority(
    provider: AIProvider, *, title: str, description: str | None = None,
    deadline: Optional[date] = None, business_impact: str | None = None,
    blocking_count: int = 0,
) -> dict[str, Any]:
    today = date.today()
    fallback = _heuristic_score(title, description, deadline, today, business_impact, blocking_count)

    from app.ai.provider import HeuristicOnlyProvider
    if isinstance(provider, HeuristicOnlyProvider):
        return fallback

    user_prompt = (
        f"Title: {title}\n"
        f"Description: {description or '(none)'}\n"
        f"Deadline: {deadline.isoformat() if deadline else '(none)'}\n"
        f"Today: {today.isoformat()}\n"
        f"Project business impact: {business_impact or '(unknown)'}\n"
        f"Tasks blocked by this one: {blocking_count}\n"
    )
    result = await provider.complete_json(_SYSTEM_PROMPT, user_prompt)
    try:
        priority = Priority(result["priority"])
        score = int(result["score"])
        reason = str(result["reason"])
    except (KeyError, ValueError, TypeError):
        return fallback

    return {"priority": priority, "score": max(0, min(100, score)), "reason": reason, "source": PrioritySource.ai}
