"""Sign-up, sign-in, sign-out and the current user (MVP FR-1, FR-2, FR-3)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select, text

from ovas_api.auth import (
    COOKIE,
    CurrentUser,
    Db,
    end_session,
    hash_password,
    start_session,
    verify_password,
)
from ovas_api.models import LoginFailure, Membership, User, Workspace

router = APIRouter(prefix="/v1", tags=["auth"])

MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=15)


class SignUp(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(default="", max_length=200)


class SignIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class Me(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    workspace_id: str
    workspace_name: str


async def _me(db: Db, user: User, workspace_id, role: str) -> Me:
    workspace = await db.get(Workspace, workspace_id)
    assert workspace is not None
    return Me(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=role,
        workspace_id=str(workspace_id),
        workspace_name=workspace.name,
    )


@router.post("/auth/signup", status_code=201)
async def signup(body: SignUp, response: Response, db: Db) -> Me:
    email = body.email.lower()
    # Serialise sign-ups so exactly one first user becomes the owner.
    await db.execute(text("SELECT pg_advisory_xact_lock(4242)"))
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists. Sign in instead.")
    workspace = await db.scalar(select(Workspace).limit(1))
    if workspace is None:
        workspace = Workspace(name="My workspace", open_signup=True)
        db.add(workspace)
        role = "owner"
    elif workspace.open_signup:
        role = "member"
    else:
        raise HTTPException(403, "Sign-up is closed. Ask the workspace owner to open it.")
    user = User(
        email=email, password_hash=hash_password(body.password), display_name=body.display_name
    )
    db.add(user)
    await db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=role))
    await start_session(db, response, user.id, workspace.id)
    await db.commit()
    return await _me(db, user, workspace.id, role)


@router.post("/auth/login")
async def login(body: SignIn, request: Request, response: Response, db: Db) -> Me:
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    keys = [f"email:{email}", f"ip:{ip}"]
    since = datetime.now(UTC) - FAILURE_WINDOW
    for key in keys:
        count = await db.scalar(
            select(func.count()).where(LoginFailure.key == key, LoginFailure.created_at > since)
        )
        if (count or 0) >= MAX_FAILURES:
            raise HTTPException(429, "Too many failed sign-ins. Wait 15 minutes and try again.")

    user = await db.scalar(select(User).where(User.email == email))
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        db.add_all([LoginFailure(key=k) for k in keys])
        await db.commit()
        raise HTTPException(401, "Email or password is incorrect.")

    membership = await db.scalar(select(Membership).where(Membership.user_id == user.id).limit(1))
    if membership is None:
        raise HTTPException(403, "This account is not a member of any workspace.")
    await db.execute(delete(LoginFailure).where(LoginFailure.key == keys[0]))
    await start_session(db, response, user.id, membership.workspace_id)
    await db.commit()
    return await _me(db, user, membership.workspace_id, membership.role)


@router.post("/auth/logout", status_code=204)
async def logout(
    response: Response, db: Db, ovas_session: Annotated[str | None, Cookie(alias=COOKIE)] = None
) -> None:
    await end_session(db, response, ovas_session)
    await db.commit()


@router.get("/me")
async def me(principal: CurrentUser, db: Db) -> Me:
    return await _me(db, principal.user, principal.workspace_id, principal.role)
