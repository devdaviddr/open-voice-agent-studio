"""Password hashing, browser sessions and the CurrentUser dependency (MVP FR-1, FR-2)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ovas_api.config import get_settings
from ovas_api.db import get_db
from ovas_api.models import Membership, User, UserSession

COOKIE = "ovas_session"
_hasher = PasswordHasher()  # argon2id with library defaults (OWASP-compliant)
# Verifying against this when the email is unknown keeps response time the same.
_DUMMY_HASH = _hasher.hash("timing-equaliser")

Db = Annotated[AsyncSession, Depends(get_db)]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


async def start_session(
    db: AsyncSession, response: Response, user_id: uuid.UUID, workspace_id: uuid.UUID
) -> None:
    token = secrets.token_urlsafe(32)
    settings = get_settings()
    now = _now()
    db.add(
        UserSession(
            token_hash=_token_hash(token),
            user_id=user_id,
            workspace_id=workspace_id,
            last_seen_at=now,
            expires_at=now + timedelta(days=settings.session_idle_days),
        )
    )
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.session_idle_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


async def end_session(db: AsyncSession, response: Response, token: str | None) -> None:
    if token:
        await db.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))
    response.delete_cookie(COOKIE, path="/")


@dataclass(frozen=True)
class Principal:
    user: User
    workspace_id: uuid.UUID
    role: str

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"


async def current_user(db: Db, ovas_session: Annotated[str | None, Cookie()] = None) -> Principal:
    if not ovas_session:
        raise HTTPException(401, "Sign in to continue.")
    row = (
        await db.execute(
            select(UserSession, User, Membership)
            .join(User, User.id == UserSession.user_id)
            .join(
                Membership,
                (Membership.user_id == UserSession.user_id)
                & (Membership.workspace_id == UserSession.workspace_id),
            )
            .where(UserSession.token_hash == _token_hash(ovas_session))
        )
    ).one_or_none()
    now = _now()
    if row is None or row.UserSession.expires_at <= now:
        raise HTTPException(401, "Your session has ended. Sign in again.")
    session = row.UserSession
    if now - session.last_seen_at > timedelta(minutes=1):  # sliding idle expiry, cheap to maintain
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=get_settings().session_idle_days)
        await db.commit()
    return Principal(user=row.User, workspace_id=session.workspace_id, role=row.Membership.role)


CurrentUser = Annotated[Principal, Depends(current_user)]


async def require_owner(principal: CurrentUser) -> Principal:
    if not principal.is_owner:
        raise HTTPException(403, "Only the workspace owner can do this.")
    return principal


Owner = Annotated[Principal, Depends(require_owner)]
