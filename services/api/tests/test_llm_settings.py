from ovas_api.config import get_settings

SECRET = "sk-test-very-secret-value"


async def test_key_is_write_only(owner, monkeypatch):  # MVP AC-19
    monkeypatch.setattr(get_settings(), "secret_key", "test-secret-key")
    default = (await owner.get("/v1/settings/llm")).json()
    assert default["configured"] is False and default["default_model"]

    body = {"base_url": "http://127.0.0.1:9/v1", "default_model": "m", "api_key": SECRET}
    res = await owner.put("/v1/settings/llm", json=body)
    assert res.status_code == 200
    assert SECRET not in res.text
    read = await owner.get("/v1/settings/llm")
    assert read.json()["api_key"] == {"set": True}
    assert SECRET not in read.text

    # Updating without a key keeps it; an empty string clears it.
    body.pop("api_key")
    assert (await owner.put("/v1/settings/llm", json=body)).json()["api_key"] == {"set": True}
    cleared = await owner.put("/v1/settings/llm", json={**body, "api_key": ""})
    assert cleared.json()["api_key"] == {"set": False}


async def test_unreachable_endpoint_reported(owner, monkeypatch):  # MVP AC-19
    monkeypatch.setattr(get_settings(), "secret_key", "test-secret-key")
    await owner.put(
        "/v1/settings/llm", json={"base_url": "http://127.0.0.1:9/v1", "default_model": "m"}
    )
    result = (await owner.post("/v1/settings/llm/test")).json()
    assert result["ok"] is False and "Could not reach" in result["error"]


async def test_members_cannot_change_llm(owner, make_client, signup):
    async with make_client() as member:
        await signup(member, "member@example.com")
        res = await member.put(
            "/v1/settings/llm", json={"base_url": "http://x.test/v1", "default_model": "m"}
        )
        assert res.status_code == 403


async def test_storing_a_key_needs_secret_key(owner, monkeypatch):
    monkeypatch.setattr(get_settings(), "secret_key", None)
    res = await owner.put(
        "/v1/settings/llm",
        json={"base_url": "http://x.test/v1", "default_model": "m", "api_key": "k"},
    )
    assert res.status_code == 400
