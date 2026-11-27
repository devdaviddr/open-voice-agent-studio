"""The workspace LLM endpoint (MVP FR-21). The API key is write-only."""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ovas_api.auth import CurrentUser, Db, Owner
from ovas_api.config import get_settings
from ovas_api.crypto import decrypt, encrypt
from ovas_api.models import LlmProvider

router = APIRouter(prefix="/v1/settings/llm", tags=["settings"])


class SecretState(BaseModel):
    set: bool


class LlmConfig(BaseModel):
    base_url: str
    default_model: str
    reasoning_effort: str | None
    api_key: SecretState
    configured: bool  # false while running on the server's built-in default


class LlmConfigUpdate(BaseModel):
    base_url: str = Field(min_length=1, max_length=500, pattern=r"^https?://")
    default_model: str = Field(min_length=1, max_length=200)
    reasoning_effort: str | None = Field(default=None, pattern=r"^(none|low|medium|high)$")
    api_key: str | None = Field(
        default=None, description="New key. Omit or null to keep the current one; '' to clear it."
    )


class LlmTest(BaseModel):
    ok: bool
    models: list[str] = []
    error: str | None = None


class ResolvedLlm(BaseModel):
    """What the runtime uses. Never returned by a public endpoint."""

    base_url: str
    model: str
    api_key: str | None
    reasoning_effort: str | None


async def resolve_llm(db: Db, workspace_id) -> ResolvedLlm:
    row = await db.scalar(select(LlmProvider).where(LlmProvider.workspace_id == workspace_id))
    if row is None:
        s = get_settings()
        return ResolvedLlm(
            base_url=s.default_llm_url,
            model=s.default_llm_model,
            api_key=None,
            reasoning_effort=s.default_llm_reasoning_effort,
        )
    return ResolvedLlm(
        base_url=row.base_url,
        model=row.default_model,
        api_key=decrypt(row.api_key_encrypted) if row.api_key_encrypted else None,
        reasoning_effort=row.reasoning_effort,
    )


@router.get("")
async def read_llm(principal: CurrentUser, db: Db) -> LlmConfig:
    row = await db.scalar(
        select(LlmProvider).where(LlmProvider.workspace_id == principal.workspace_id)
    )
    if row is None:
        r = await resolve_llm(db, principal.workspace_id)
        return LlmConfig(
            base_url=r.base_url,
            default_model=r.model,
            reasoning_effort=r.reasoning_effort,
            api_key=SecretState(set=False),
            configured=False,
        )
    return LlmConfig(
        base_url=row.base_url,
        default_model=row.default_model,
        reasoning_effort=row.reasoning_effort,
        api_key=SecretState(set=row.api_key_encrypted is not None),
        configured=True,
    )


@router.put("")
async def update_llm(body: LlmConfigUpdate, owner: Owner, db: Db) -> LlmConfig:
    row = await db.scalar(select(LlmProvider).where(LlmProvider.workspace_id == owner.workspace_id))
    if row is None:
        row = LlmProvider(workspace_id=owner.workspace_id, base_url="", default_model="")
        db.add(row)
    row.base_url = body.base_url.rstrip("/")
    row.default_model = body.default_model
    row.reasoning_effort = body.reasoning_effort
    if body.api_key == "":
        row.api_key_encrypted = None
    elif body.api_key is not None:
        row.api_key_encrypted = encrypt(body.api_key)
    await db.commit()
    return await read_llm(owner, db)


@router.post("/test")
async def test_llm(principal: CurrentUser, db: Db) -> LlmTest:
    llm = await resolve_llm(db, principal.workspace_id)
    headers = {"authorization": f"Bearer {llm.api_key}"} if llm.api_key else {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(f"{llm.base_url}/models", headers=headers)
            res.raise_for_status()
            models = sorted(m["id"] for m in res.json().get("data", []))
    except httpx.HTTPStatusError as e:
        return LlmTest(ok=False, error=f"The endpoint answered {e.response.status_code}.")
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return LlmTest(ok=False, error=f"Could not reach {llm.base_url}: {type(e).__name__}")
    if llm.model not in models:
        return LlmTest(
            ok=False, models=models, error=f"Model '{llm.model}' is not available there."
        )
    return LlmTest(ok=True, models=models)
