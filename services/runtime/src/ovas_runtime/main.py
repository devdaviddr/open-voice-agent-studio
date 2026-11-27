"""Runtime: hosts live agent sessions. Text over WebSocket in the MVP; voice arrives in M2."""

import asyncio
import contextlib
import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ovas_core.engine import TextSession
from ovas_core.spec import AgentSpec
from ovas_core.tokens import verify_session
from ovas_runtime import __version__
from ovas_runtime.api_client import ApiClient
from ovas_runtime.config import get_settings
from ovas_runtime.llm import OpenAICompatibleLlm

log = logging.getLogger("ovas.runtime")
app = FastAPI(title="Open Voice Agent Studio runtime", version=__version__)

# Streamed tokens go to the browser but are not stored; the full message is.
NOT_STORED = {"token"}


def make_llm(llm: dict[str, Any]) -> OpenAICompatibleLlm:
    return OpenAICompatibleLlm(
        base_url=llm["base_url"],
        default_model=llm["model"],
        api_key=llm.get("api_key"),
        reasoning_effort=llm.get("reasoning_effort"),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.websocket("/v1/sessions/{session_id}/stream")
async def stream(ws: WebSocket, session_id: str, token: str = "") -> None:
    if verify_session(token, get_settings().internal_key) != session_id:
        await ws.close(code=4401, reason="Invalid or expired session token")
        return
    api = ApiClient()
    try:
        data = await api.session(session_id)
    except Exception:
        await api.aclose()
        await ws.close(code=4404, reason="Session not found")
        return
    if data["ended"]:
        await api.aclose()
        await ws.close(code=4409, reason="Session already ended")
        return
    await ws.accept()

    stored: list[dict[str, Any]] = []
    lock = asyncio.Lock()

    async def emit(kind: str, payload: dict[str, Any]) -> None:
        await ws.send_text(json.dumps({"type": kind, **payload}, default=str))
        if kind not in NOT_STORED:
            async with lock:
                stored.append({"type": kind, "payload": payload})

    async def flush() -> None:
        async with lock:
            batch, stored[:] = list(stored), []
        try:
            await api.events(session_id, batch)
        except Exception:  # keep the conversation going; the events are logged instead
            log.exception("could not store %d events for %s", len(batch), session_id)

    session = TextSession(
        spec=AgentSpec.model_validate(data["spec"]),
        llm=make_llm(data["llm"]),
        emit=emit,
        default_model=data["llm"]["model"],
        variables=dict(data["variables"]),
    )
    try:
        await session.start()
        await flush()
        while not session.ended:
            message = json.loads(await ws.receive_text())
            if message.get("type") == "user_message" and str(message.get("text", "")).strip():
                await emit("user_message", {"text": message["text"]})
                try:
                    await session.user_message(str(message["text"]))
                except Exception as e:  # model or network failure: tell the user, keep the session
                    log.exception("turn failed in %s", session_id)
                    await emit(
                        "error", {"message": f"The agent could not reply: {type(e).__name__}"}
                    )
                await flush()
            elif message.get("type") == "end":
                await session.end("ended_by_user")
    except WebSocketDisconnect:
        await session.end("disconnected")
    finally:
        await flush()
        try:
            await api.end(
                session_id,
                {
                    "outcome": session.outcome,
                    "variables": session.variables,
                    "usage": session.usage,
                },
            )
        except Exception:
            log.exception("could not close session %s", session_id)
        await api.aclose()
        with contextlib.suppress(RuntimeError):  # already closed by the client
            await ws.close()
