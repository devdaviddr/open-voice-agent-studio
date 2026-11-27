"""Calls to the API's /internal endpoints."""

from typing import Any

import httpx

from ovas_runtime.config import get_settings


class ApiClient:
    def __init__(self) -> None:
        s = get_settings()
        self.http = httpx.AsyncClient(
            base_url=s.api_url, headers={"x-internal-key": s.internal_key}, timeout=10.0
        )

    async def session(self, session_id: str) -> dict[str, Any]:
        res = await self.http.get(f"/internal/sessions/{session_id}")
        res.raise_for_status()
        return res.json()

    async def events(self, session_id: str, events: list[dict[str, Any]]) -> None:
        if events:
            res = await self.http.post(f"/internal/sessions/{session_id}/events", json=events)
            res.raise_for_status()

    async def end(self, session_id: str, body: dict[str, Any]) -> None:
        res = await self.http.post(f"/internal/sessions/{session_id}/end", json=body)
        res.raise_for_status()

    async def aclose(self) -> None:
        await self.http.aclose()
