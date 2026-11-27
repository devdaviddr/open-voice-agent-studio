"""Workspace settings (MVP FR-2: open sign-up)."""

from fastapi import APIRouter
from pydantic import BaseModel

from ovas_api.auth import CurrentUser, Db, Owner
from ovas_api.models import Workspace

router = APIRouter(prefix="/v1", tags=["settings"])


class WorkspaceSettings(BaseModel):
    name: str
    open_signup: bool


class WorkspaceSettingsPatch(BaseModel):
    name: str | None = None
    open_signup: bool | None = None


@router.get("/settings")
async def get_settings(principal: CurrentUser, db: Db) -> WorkspaceSettings:
    ws = await db.get(Workspace, principal.workspace_id)
    assert ws is not None
    return WorkspaceSettings(name=ws.name, open_signup=ws.open_signup)


@router.patch("/settings")
async def patch_settings(body: WorkspaceSettingsPatch, owner: Owner, db: Db) -> WorkspaceSettings:
    ws = await db.get(Workspace, owner.workspace_id)
    assert ws is not None
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ws, field, value)
    await db.commit()
    return WorkspaceSettings(name=ws.name, open_signup=ws.open_signup)
