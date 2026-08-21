import uuid
from datetime import datetime, date, time, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.calendar import CalendarEvent
from app.repositories.base import WorkspaceScopedRepository

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarEventCreate(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime
    attendees: list[str] | None = None
    location: str | None = None


def _repo(db: AsyncSession) -> WorkspaceScopedRepository[CalendarEvent]:
    return WorkspaceScopedRepository(CalendarEvent, db)


def _parse_google_datetime(value) -> datetime | None:
    """
    Convert Google Calendar date/datetime values to Python datetime.

    Google can return:
    - '2026-08-22'
    - '2026-08-22T10:00:00+06:00'
    - '2026-08-22T10:00:00Z'
    """

    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(
            value,
            time.min,
            tzinfo=timezone.utc,
        )

    if not isinstance(value, str):
        return None

    value = value.strip()

    # All-day Google Calendar event.
    # Google returns a date without time.
    if len(value) == 10:
        parsed_date = date.fromisoformat(value)

        return datetime.combine(
            parsed_date,
            time.min,
            tzinfo=timezone.utc,
        )

    # Normal Google datetime.
    normalized = value.replace("Z", "+00:00")

    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


@router.get("")
async def list_events(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    items = await _repo(db).list(
        ctx.workspace_id,
        limit=100,
    )

    return [
        {
            "id": str(i.id),
            "title": i.title,
            "starts_at": i.starts_at.isoformat(),
            "ends_at": i.ends_at.isoformat(),
            "attendees": i.attendees,
            "location": i.location,
        }
        for i in items
    ]


@router.post("", status_code=201)
async def create_event(
    payload: CalendarEventCreate,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    item = await _repo(db).create(
        ctx.workspace_id,
        owner_id=ctx.user.id,
        **payload.model_dump(),
    )

    return {
        "id": str(item.id),
    }


@router.post("/sync")
async def sync_from_google(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    """Pull upcoming events from the connected Google account."""

    from app.models.system import IntegrationAccount
    from app.integrations.google import GoogleWorkspaceClient
    from app.api.v1.integrations import get_valid_access_token

    result = await db.execute(
        select(IntegrationAccount)
        .where(
            IntegrationAccount.workspace_id == ctx.workspace_id,
            IntegrationAccount.user_id == ctx.user.id,
            IntegrationAccount.provider == "google",
            IntegrationAccount.is_active.is_(True),
        )
        .order_by(IntegrationAccount.id.desc())
        .limit(1)
    )

    account = result.scalars().first()

    if not account or not account.access_token:
        return {
            "synced": 0,
            "detail": (
                "No connected Google account. "
                "Connect one via /integrations/google/connect."
            ),
        }

    access_token = await get_valid_access_token(
        account,
        db,
    )

    if not access_token:
        return {
            "synced": 0,
            "detail": (
                "Stored Google token could not be decrypted "
                "or refreshed - reconnect the account in Settings."
            ),
        }

    client = GoogleWorkspaceClient(access_token)

    events = await client.list_upcoming_events()

    count = 0
    skipped = 0

    for event in events:

        if not event.get("starts_at") or not event.get("ends_at"):
            skipped += 1
            continue

        starts_at = _parse_google_datetime(
            event.get("starts_at")
        )

        ends_at = _parse_google_datetime(
            event.get("ends_at")
        )

        if not starts_at or not ends_at:
            skipped += 1
            continue

        external_id = event.get("external_id")

        # Do not create duplicate events.
        existing = None

        if external_id:
            existing_result = await db.execute(
                select(CalendarEvent)
                .where(
                    CalendarEvent.workspace_id == ctx.workspace_id,
                    CalendarEvent.external_id == external_id,
                )
                .limit(1)
            )

            existing = existing_result.scalars().first()

        if existing:
            # Update existing event.
            existing.title = event.get(
                "title",
                existing.title,
            )
            existing.starts_at = starts_at
            existing.ends_at = ends_at
            existing.attendees = event.get(
                "attendees"
            )
            existing.location = event.get(
                "location"
            )

            continue

        db.add(
            CalendarEvent(
                workspace_id=ctx.workspace_id,
                owner_id=ctx.user.id,
                external_id=external_id,
                title=event.get(
                    "title",
                    "Untitled event",
                ),
                starts_at=starts_at,
                ends_at=ends_at,
                attendees=event.get("attendees"),
                location=event.get("location"),
            )
        )

        count += 1

    await db.commit()

    return {
        "synced": count,
        "skipped": skipped,
    }
