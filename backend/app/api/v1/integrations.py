import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.dependencies import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.integrations.google import GoogleWorkspaceClient
from app.models.enums import InboxSource
from app.models.opportunity import Opportunity
from app.models.risk import Risk
from app.models.system import InboxItem, IntegrationAccount

logger = logging.getLogger("operator-ai.integrations")


async def refresh_google_token(
    account: IntegrationAccount,
    db: AsyncSession,
) -> str | None:
    """Refresh an expired Google access token."""

    refresh_token = decrypt_secret(account.refresh_token)

    if not refresh_token:
        logger.warning(
            "No refresh token for account %s",
            account.id,
        )
        return None

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

        if resp.status_code != 200:
            logger.warning(
                "Google token refresh failed for account %s: %s",
                account.id,
                resp.status_code,
            )
            return None

        data = resp.json()

    new_access = data.get("access_token")
    new_refresh = data.get("refresh_token")
    expires_in = data.get("expires_in", 3600)

    if not new_access:
        logger.warning(
            "Google token refresh returned no access token for account %s",
            account.id,
        )
        return None

    account.access_token = encrypt_secret(new_access)

    if new_refresh:
        account.refresh_token = encrypt_secret(new_refresh)

    account.token_expires_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=expires_in)
    )

    await db.commit()

    return new_access


async def get_valid_access_token(
    account: IntegrationAccount,
    db: AsyncSession,
) -> str | None:
    """Return a valid Google access token."""

    access_token = decrypt_secret(account.access_token)

    if not access_token:
        return None

    if account.token_expires_at:
        now = datetime.now(timezone.utc)

        if account.token_expires_at - now > timedelta(minutes=5):
            return access_token

        refreshed = await refresh_google_token(account, db)

        if refreshed:
            return refreshed

        # Old token may still work for a short period.
        return access_token

    return access_token


async def get_google_account(
    ctx: WorkspaceContext,
    db: AsyncSession,
    active_only: bool = True,
) -> IntegrationAccount | None:
    """
    Get one Google account.

    Older versions of the application could create duplicate
    IntegrationAccount rows. Therefore this function deliberately
    uses .limit(1) instead of scalar_one_or_none().
    """

    conditions = [
        IntegrationAccount.workspace_id == ctx.workspace_id,
        IntegrationAccount.user_id == ctx.user.id,
        IntegrationAccount.provider == "google",
    ]

    if active_only:
        conditions.append(
            IntegrationAccount.is_active == True  # noqa: E712
        )

    result = await db.execute(
        select(IntegrationAccount)
        .where(*conditions)
        .order_by(
            IntegrationAccount.is_active.desc(),
            IntegrationAccount.id.desc(),
        )
        .limit(1)
    )

    return result.scalars().first()


async def deactivate_duplicate_google_accounts(
    ctx: WorkspaceContext,
    db: AsyncSession,
    keep_account_id,
) -> None:
    """
    Deactivate duplicate Google accounts for this workspace/user.
    Keeps only the selected account active.
    """

    result = await db.execute(
        select(IntegrationAccount).where(
            IntegrationAccount.workspace_id == ctx.workspace_id,
            IntegrationAccount.user_id == ctx.user.id,
            IntegrationAccount.provider == "google",
            IntegrationAccount.id != keep_account_id,
            IntegrationAccount.is_active == True,  # noqa: E712
        )
    )

    duplicates = result.scalars().all()

    if duplicates:
        logger.warning(
            "Found %s duplicate Google integration accounts "
            "for workspace=%s user=%s. Deactivating them.",
            len(duplicates),
            ctx.workspace_id,
            ctx.user.id,
        )

    for duplicate in duplicates:
        duplicate.is_active = False


router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
)


_RISK_OPP_SYSTEM_PROMPT = """You scan recent email metadata for an AI Chief-of-Staff.
Given a list of {sender, subject, snippet}, return ONLY JSON:
{"risks": [{"title": "...", "description": "...", "severity": "low|medium|high|critical",
"recommended_action": "...", "source_reference": "<subject or sender>"}],
"opportunities": [{"title": "...", "description": "...", "recommended_action": "...",
"source_reference": "<subject or sender>"}]}
Only include items with a clear signal in the text - do not invent risks that aren't supported by the input."""


@router.get("/google/connect")
async def connect_google():
    """
    Start Google DATA-SYNC OAuth flow.
    """

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth is not configured "
                "(set GOOGLE_CLIENT_ID/SECRET)"
            ),
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_INTEGRATION_REDIRECT_URI,
        "response_type": "code",
        "scope": settings.GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }

    return {
        "authorize_url": (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"{urlencode(params)}"
        )
    }


@router.get("/google/status")
async def google_connection_status(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Check whether Google is connected.

    Does not use scalar_one_or_none(), because old duplicate
    IntegrationAccount rows may exist.
    """

    account = await get_google_account(
        ctx=ctx,
        db=db,
        active_only=True,
    )

    if not account:
        return {
            "connected": False,
        }

    return {
        "connected": True,
        "email": account.email,
        "scopes": account.scopes,
    }


@router.post("/google/callback")
async def google_connect_callback(
    code: str,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete Google OAuth flow and save/update the integration.
    """

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured",
        )

    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_INTEGRATION_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_resp.status_code != 200:
            logger.error(
                "Google token exchange failed: %s %s",
                token_resp.status_code,
                token_resp.text,
            )

            raise HTTPException(
                status_code=400,
                detail="Google token exchange failed",
            )

        tokens = token_resp.json()

        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Google did not return an access token",
            )

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        email = None

        if userinfo_resp.status_code == 200:
            email = userinfo_resp.json().get("email")

    # IMPORTANT:
    # Do not use scalar_one_or_none() here.
    # There may already be duplicate Google accounts.
    result = await db.execute(
        select(IntegrationAccount)
        .where(
            IntegrationAccount.workspace_id == ctx.workspace_id,
            IntegrationAccount.user_id == ctx.user.id,
            IntegrationAccount.provider == "google",
        )
        .order_by(
            IntegrationAccount.is_active.desc(),
            IntegrationAccount.id.desc(),
        )
        .limit(1)
    )

    existing = result.scalars().first()

    expires_in = tokens.get("expires_in", 3600)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=expires_in)
    )

    refresh_token = tokens.get("refresh_token")

    fields = {
        "email": email,
        "access_token": encrypt_secret(access_token),
        "token_expires_at": expires_at,
        "scopes": settings.GOOGLE_SCOPES,
        "is_active": True,
    }

    # Google sometimes does not return a refresh_token
    # on subsequent OAuth connections.
    # Therefore preserve the existing refresh token.
    if refresh_token:
        fields["refresh_token"] = encrypt_secret(refresh_token)

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)

        account = existing

        logger.info(
            "Updated existing Google integration account %s",
            account.id,
        )

    else:
        account = IntegrationAccount(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.id,
            provider="google",
            **fields,
        )

        db.add(account)

        await db.flush()

        logger.info(
            "Created Google integration account %s",
            account.id,
        )

    # Deactivate any old duplicate accounts.
    await deactivate_duplicate_google_accounts(
        ctx=ctx,
        db=db,
        keep_account_id=account.id,
    )

    await db.commit()

    return {
        "connected": True,
        "email": email,
    }


@router.post("/gmail/scan")
async def scan_gmail_for_risks_and_opportunities(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Pull recent Gmail messages and classify them.
    """

    account = await get_google_account(
        ctx=ctx,
        db=db,
        active_only=True,
    )

    if not account or not account.access_token:
        return {
            "connected": False,
            "detail": (
                "No Gmail account connected. "
                "Call /integrations/google/connect first."
            ),
            "risks": [],
            "opportunities": [],
        }

    access_token = await get_valid_access_token(
        account,
        db,
    )

    if not access_token:
        return {
            "connected": False,
            "detail": (
                "Stored Google token could not be decrypted "
                "or refreshed - reconnect the account."
            ),
            "risks": [],
            "opportunities": [],
        }

    client = GoogleWorkspaceClient(access_token)

    messages = await client.list_recent_messages(
        max_results=5,
    )

    if not messages:
        return {
            "connected": True,
            "scanned": 0,
            "risks": [],
            "opportunities": [],
        }

    # Gmail -> Universal Inbox.
    from app.api.v1.inbox import _CLASSIFY_SYSTEM_PROMPT

    inbox_created = 0

    for message in messages:
        raw_text = (
            f"From: {message.get('sender', '')}\n"
            f"Subject: {message.get('subject', '')}\n"
            f"Message: {message.get('snippet', '')}"
        )

        # Do not import the same Gmail message twice.
        existing_result = await db.execute(
            select(InboxItem)
            .where(
                InboxItem.workspace_id == ctx.workspace_id,
                InboxItem.source == InboxSource.email,
                InboxItem.raw_text == raw_text,
            )
            .limit(1)
        )

        existing = existing_result.scalars().first()

        if existing:
            continue

        suggestion = await get_ai_provider().complete_json(
            _CLASSIFY_SYSTEM_PROMPT,
            raw_text,
        )

        db.add(
            InboxItem(
                workspace_id=ctx.workspace_id,
                raw_text=raw_text,
                source=InboxSource.email,
                type=suggestion.get("type"),
                ai_suggestion=suggestion,
                created_by=ctx.user.id,
            )
        )

        inbox_created += 1

    result = await get_ai_provider().complete_json(
        _RISK_OPP_SYSTEM_PROMPT,
        str(
            [
                {
                    "sender": m["sender"],
                    "subject": m["subject"],
                    "snippet": m["snippet"],
                }
                for m in messages
            ]
        ),
    )

    created_risks = []
    created_opps = []

    for r in result.get("risks", []):
        item = Risk(
            workspace_id=ctx.workspace_id,
            title=r.get("title", "Untitled risk"),
            description=r.get("description"),
            severity=r.get("severity", "medium"),
            recommended_action=r.get("recommended_action"),
            source_reference=r.get("source_reference"),
            detected_by="ai",
        )

        db.add(item)
        created_risks.append(
            r.get("title")
        )

    for o in result.get("opportunities", []):
        item = Opportunity(
            workspace_id=ctx.workspace_id,
            title=o.get(
                "title",
                "Untitled opportunity",
            ),
            description=o.get("description"),
            recommended_action=o.get("recommended_action"),
            source_reference=o.get("source_reference"),
            detected_by="ai",
        )

        db.add(item)
        created_opps.append(
            o.get("title")
        )

    await db.commit()

    return {
        "connected": True,
        "scanned": len(messages),
        "inbox_created": inbox_created,
        "risks_created": created_risks,
        "opportunities_created": created_opps,
    }
