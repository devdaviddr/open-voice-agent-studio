from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from ovas_api.db import get_engine


async def agent_with_draft(c) -> tuple[str, dict]:
    agent = (await c.post("/v1/agents", json={"name": "Ava", "template": "receptionist"})).json()
    draft = (await c.get(f"/v1/agents/{agent['id']}/draft")).json()
    return agent["id"], draft


async def save(c, agent_id: str, draft: dict) -> dict:
    res = await c.put(f"/v1/agents/{agent_id}/draft", json=draft)
    assert res.status_code == 200, res.text
    return res.json()


async def test_publish_freezes_draft_and_moves_live(owner):  # MVP AC-10
    agent_id, draft = await agent_with_draft(owner)
    v1 = await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "First"})
    assert v1.status_code == 201
    assert v1.json()["number"] == 1 and v1.json()["is_live"]

    draft["spec"]["settings"]["prompt"] = "Changed after v1"
    draft = await save(owner, agent_id, draft)
    stored = (await owner.get(f"/v1/agents/{agent_id}/versions/1")).json()
    assert stored["spec"]["settings"]["prompt"] != "Changed after v1"

    v2 = (await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "Second"})).json()
    assert v2["number"] == 2
    assert (await owner.get(f"/v1/agents/{agent_id}")).json()["live_version"] == 2

    back = await owner.put(f"/v1/agents/{agent_id}/live", json={"version": 1})
    assert back.json()["is_live"]
    assert (await owner.get(f"/v1/agents/{agent_id}")).json()["live_version"] == 1
    listed = (await owner.get(f"/v1/agents/{agent_id}/versions")).json()
    assert [(v["number"], v["is_live"]) for v in listed] == [(2, False), (1, True)]
    assert listed[0]["author"] == "owner@example.com"


async def test_versions_cannot_be_updated_in_the_database(owner):  # product AC-10
    agent_id, _ = await agent_with_draft(owner)
    await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "First"})
    async with get_engine().begin() as conn:
        try:
            await conn.execute(text("UPDATE agent_versions SET message = 'tampered'"))
            raise AssertionError("update should have been rejected")
        except DBAPIError as e:
            assert "immutable" in str(e)


async def test_publish_blocked_while_draft_has_problems(owner):
    agent_id, draft = await agent_with_draft(owner)
    draft["spec"]["graph"]["edges"] = []
    await save(owner, agent_id, draft)
    res = await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "Broken"})
    assert res.status_code == 422
    assert {i["code"] for i in res.json()["issues"]} >= {"unreachable"}
    assert (await owner.get(f"/v1/agents/{agent_id}/versions")).json() == []


async def test_restore_copies_version_into_draft(owner):
    agent_id, draft = await agent_with_draft(owner)
    await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "First"})
    draft["spec"]["settings"]["prompt"] = "Experiment"
    draft = await save(owner, agent_id, draft)
    restored = (await owner.post(f"/v1/agents/{agent_id}/versions/1/restore")).json()
    assert restored["revision"] == draft["revision"] + 1
    assert restored["spec"]["settings"]["prompt"] != "Experiment"


async def test_diff_draft_against_version(owner):  # MVP AC-11
    agent_id, draft = await agent_with_draft(owner)
    await owner.post(f"/v1/agents/{agent_id}/versions", json={"message": "First"})
    for node in draft["spec"]["graph"]["nodes"]:
        if node["id"] == "faq":
            node["data"]["prompt"] += " Mention parking."
    draft["spec"]["graph"]["edges"] = [
        e for e in draft["spec"]["graph"]["edges"] if e["id"] != "e-bye"
    ]
    await save(owner, agent_id, draft)
    res = (
        await owner.get(f"/v1/agents/{agent_id}/diff", params={"from": "1", "to": "draft"})
    ).json()
    assert [(c["kind"], c["change"], c["id"]) for c in res["changes"]] == [
        ("node", "changed", "faq"),
        ("edge", "removed", "e-bye"),
    ]
    assert (await owner.get(f"/v1/agents/{agent_id}/diff", params={"from": "9"})).status_code == 404


async def test_unknown_version_404(owner):
    agent_id, _ = await agent_with_draft(owner)
    assert (await owner.get(f"/v1/agents/{agent_id}/versions/3")).status_code == 404
    assert (await owner.put(f"/v1/agents/{agent_id}/live", json={"version": 3})).status_code == 404
