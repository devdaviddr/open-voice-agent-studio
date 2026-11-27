import uuid

from sqlalchemy import insert

from ovas_api.db import get_engine
from ovas_api.models import Agent, Workspace
from ovas_core.spec import blank_spec


async def create(c, **body) -> dict:
    res = await c.post("/v1/agents", json={"name": "Ava", **body})
    assert res.status_code == 201, res.text
    return res.json()


async def test_create_from_template_duplicate_delete(owner):  # MVP AC-4
    agent = await create(owner, template="receptionist")
    draft = (await owner.get(f"/v1/agents/{agent['id']}/draft")).json()
    types = {n["type"] for n in draft["spec"]["graph"]["nodes"]}
    assert types == {"start", "agent_step", "extract", "router", "end", "note"}

    copy = (await owner.post(f"/v1/agents/{agent['id']}/duplicate")).json()
    assert copy["name"] == "Copy of Ava"
    assert copy["live_version"] is None
    copy_draft = (await owner.get(f"/v1/agents/{copy['id']}/draft")).json()
    assert copy_draft["spec"] == draft["spec"]

    assert (await owner.delete(f"/v1/agents/{agent['id']}")).status_code == 204
    assert (await owner.get(f"/v1/agents/{agent['id']}")).status_code == 404
    assert [a["id"] for a in (await owner.get("/v1/agents")).json()] == [copy["id"]]


async def test_rename(owner):
    agent = await create(owner)
    res = await owner.patch(f"/v1/agents/{agent['id']}", json={"name": "Reception"})
    assert res.json()["name"] == "Reception"


async def test_stale_revision_conflicts(owner):  # MVP AC-6
    agent = await create(owner)
    draft = (await owner.get(f"/v1/agents/{agent['id']}/draft")).json()

    first = dict(draft)
    first["spec"]["settings"]["prompt"] = "Tab one"
    saved = await owner.put(f"/v1/agents/{agent['id']}/draft", json=first)
    assert saved.status_code == 200
    assert saved.json()["revision"] == draft["revision"] + 1

    second = dict(draft)  # still based on the old revision
    second["spec"]["settings"]["prompt"] = "Tab two"
    conflict = await owner.put(f"/v1/agents/{agent['id']}/draft", json=second)
    assert conflict.status_code == 409
    assert conflict.json()["current_revision"] == draft["revision"] + 1
    latest = (await owner.get(f"/v1/agents/{agent['id']}/draft")).json()
    assert latest["spec"]["settings"]["prompt"] == "Tab one"


async def test_invalid_spec_rejected(owner):
    agent = await create(owner)
    bad = {"revision": 1, "spec": {"graph": {"nodes": [{"id": "x", "type": "warp"}]}}}
    assert (await owner.put(f"/v1/agents/{agent['id']}/draft", json=bad)).status_code == 422


async def test_other_workspace_agents_invisible(owner):  # MVP AC-2
    mine = await create(owner)
    other_ws = uuid.uuid4()
    other_agent = uuid.uuid4()
    async with get_engine().begin() as conn:
        await conn.execute(insert(Workspace).values(id=other_ws, name="Other", open_signup=True))
        await conn.execute(
            insert(Agent).values(
                id=other_agent,
                workspace_id=other_ws,
                name="Secret",
                description="",
                draft=blank_spec().model_dump(mode="json"),
                draft_revision=1,
            )
        )
    listed = [a["id"] for a in (await owner.get("/v1/agents")).json()]
    assert listed == [mine["id"]]
    for method, path in [
        ("GET", f"/v1/agents/{other_agent}"),
        ("GET", f"/v1/agents/{other_agent}/draft"),
        ("PATCH", f"/v1/agents/{other_agent}"),
        ("DELETE", f"/v1/agents/{other_agent}"),
        ("POST", f"/v1/agents/{other_agent}/duplicate"),
    ]:
        res = await owner.request(method, path, json={} if method == "PATCH" else None)
        assert res.status_code == 404, (method, path)
    put = await owner.put(
        f"/v1/agents/{other_agent}/draft",
        json={"revision": 1, "spec": blank_spec().model_dump(mode="json")},
    )
    assert put.status_code == 404


async def test_validate_reports_issues(owner):  # MVP AC-7 (API)
    agent = await create(owner)
    spec = blank_spec().model_dump(mode="json")
    spec["graph"]["edges"] = []
    issues = (await owner.post(f"/v1/agents/{agent['id']}/validate", json=spec)).json()["issues"]
    assert {i["code"] for i in issues} >= {"unreachable", "dead_end"}


async def test_requires_sign_in(client):
    assert (await client.get("/v1/agents")).status_code == 401
