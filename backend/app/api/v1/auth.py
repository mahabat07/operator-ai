import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password,
)
from app.db.session import get_db
from app.models.enums import AuthProvider, WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def _provision_user_and_workspace(
    db: AsyncSession, *, email: str, full_name: str, workspace_name: str,
    password_hash: str | None, auth_provider: AuthProvider, google_id: str | None = None,
    avatar_url: str | None = None,
) -> User:
    user = User(email=email, full_name=full_name, password_hash=password_hash,
                auth_provider=auth_provider, google_id=google_id, avatar_url=avatar_url)
    db.add(user)
    await db.flush()

    workspace = Workspace(name=workspace_name)
    db.add(workspace)
    await db.flush()

    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner))
    user.current_workspace_id = workspace.id
    await db.commit()
    await db.refresh(user)
    return user


def _tokens_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.current_workspace_id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await _provision_user_and_workspace(
        db, email=payload.email, full_name=payload.full_name, workspace_name=payload.workspace_name,
        password_hash=hash_password(payload.password), auth_provider=AuthProvider.password,
    )
    return AuthResponse(user=UserResponse.model_validate(user), tokens=_tokens_for(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(user=UserResponse.model_validate(user), tokens=_tokens_for(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError
        user_id = uuid.UUID(data["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _tokens_for(user)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


# ---------- Google OAuth login (separate from data-sync scopes, see
# integrations.py for the Gmail/Calendar/Drive connect flow) ----------
@router.get("/google/login")
async def google_login():
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID or "",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on this server",
        )

    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Google token exchange failed",
            )

        google_access_token = token_resp.json()["access_token"]

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        userinfo_resp.raise_for_status()
        info = userinfo_resp.json()

    user = (
        await db.execute(
            select(User).where(User.google_id == info["sub"])
        )
    ).scalar_one_or_none()

    if user is None:
        user = (
            await db.execute(
                select(User).where(User.email == info["email"])
            )
        ).scalar_one_or_none()

    if user is None:
        user = await _provision_user_and_workspace(
            db,
            email=info["email"],
            full_name=info.get("name", info["email"]),
            workspace_name=f"{info.get('given_name', 'My')} Workspace",
            password_hash=None,
            auth_provider=AuthProvider.google,
            google_id=info["sub"],
            avatar_url=info.get("picture"),
        )

    tokens = _tokens_for(user)

    frontend_url = (
        "http://localhost:3001/oauth/callback"
        f"#access_token={tokens.access_token}"
        f"&refresh_token={tokens.refresh_token}"
    )

    return RedirectResponse(url=frontend_url)
