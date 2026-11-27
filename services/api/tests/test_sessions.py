from urllib.parse import parse_qs, urlparse

from ovas_api.config import get_settings
from ovas_core.tokens import verify_session


async def new_agent(c, template="receptionist") -> str:
    return (await c.post("/v1/agents", json={"name": "Ava", "template": template})).json()["id"]


def internal_headers() -> dict:
    return {"x-internal-key": get_settings().internal_key}


async def test_start_draft_session_and_runtime_flow(owner):  # MVP AC-18
    agent_id = await new_agent(owner)
    res = await owner.post(
        "/v1/sessions", json={"agent_id": agent_id, "end_user_id": "ana", "variables": {"x": 1}}
    )
    assert res.status_code == 201, res.text
    started = res.json()
    url = urlparse(started["stream_url"])
    assert url.path == f"/rt/v1/sessions/{started['session_id']}/stream"
    token = parse_qs(url.query)["token"][0]
    assert verify_session(token, get_settings().internal_key) == started["session_id"]

    sid = started["session_id"]
    assert (await owner.get(f"/internal/sessions/{sid}")).status_code == 403
    runtime = (await owner.get(f"/internal/sessions/{sid}", headers=internal_headers())).json()
    assert runtime["end_user_id"] == "ana" and runtime["variables"] == {"x": 1}
    assert runtime["llm"]["model"] and "api_key" in runtime["llm"]

    events = [{"type": "node_enter", "payload": {"node_id": "start"}}]
    events.append({"type": "assistant_message", "payload": {"text": "Hi"}})
    await owner.post(f"/internal/sessions/{sid}/events", json=events, headers=internal_headers())
    await owner.post(
        f"/internal/sessions/{sid}/events",
        json=[{"type": "user_message", "payload": {"text": "Hello"}}],
        headers=internal_headers(),
    )
    await owner.post(
        f"/internal/sessions/{sid}/end",
        json={"outcome": "booked", "variables": {"x": 2}, "usage": {"turns": 1}},
        headers=internal_headers(),
    )
    detail = (await owner.get(f"/v1/sessions/{sid}")).json()
    assert [e["seq"] for e in detail["events"]] == [1, 2, 3]
    assert detail["events"][2]["payload"]["text"] == "Hello"
    assert detail["outcome"] == "booked" and detail["turns"] == 1
    assert detail["draft_revision"] == 1 and detail["version_number"] is None
    listed = (await owner.get("/v1/sessions", params={"agent_id": agent_id})).json()
    assert [s["id"] for s in listed] == [sid]


async def test_invalid_draft_cannot_be_tested(owner):
    agent_id = await new_agent(owner)
    draft = (await owner.get(f"/v1/agents/{agent_id}/draft")).json()
    draft["spec"]["graph"]["edges"] = []
    await owner.put(f"/v1/agents/{agent_id}/draft", json=draft)
    res = await owner.post("/v1/sessions", json={"agent_id": agent_id})
    assert res.status_code == 422 and res.json()["issues"]


async def test_live_target_needs_a_published_version(owner):
    agent_id = await new_agent(owner)
    assert (
        await owner.post("/v1/sessions", json={"agent_id": agent_id, "target": "live"})
    ).status_code == 422
    await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "v1"})
    res = await owner.post("/v1/sessions", json={"agent_id": agent_id, "target": "live"})
    sid = res.json()["session_id"]
    assert (await owner.get(f"/v1/sessions/{sid}")).json()["version_number"] == 1


async def test_delete_session(owner):
    agent_id = await new_agent(owner)
    sid = (await owner.post("/v1/sessions", json={"agent_id": agent_id})).json()["session_id"]
    assert (await owner.delete(f"/v1/sessions/{sid}")).status_code == 204
    assert (await owner.get(f"/v1/sessions/{sid}")).status_code == 404
