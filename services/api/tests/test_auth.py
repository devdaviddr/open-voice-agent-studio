async def test_signup_signin_signout(client, make_client, signup):  # MVP AC-1
    me = await signup(client, "Ana@Example.com")
    assert me["email"] == "ana@example.com"
    assert (await client.get("/v1/me")).status_code == 200

    cookie = client.cookies.get("ovas_session")
    assert (await client.post("/v1/auth/logout")).status_code == 204
    assert (await client.get("/v1/me")).status_code == 401

    async with make_client() as stale:  # the old cookie is dead server-side, not just cleared
        stale.cookies.set("ovas_session", cookie)
        assert (await stale.get("/v1/me")).status_code == 401

    bad = await client.post(
        "/v1/auth/login", json={"email": "ana@example.com", "password": "nope-nope-nope"}
    )
    assert bad.status_code == 401
    good = await client.post(
        "/v1/auth/login", json={"email": "ana@example.com", "password": "correct horse battery"}
    )
    assert good.status_code == 200
    assert (await client.get("/v1/me")).json()["email"] == "ana@example.com"


async def test_short_password_rejected(client, make_client, signup):  # MVP AC-1
    res = await client.post("/v1/auth/signup", json={"email": "a@example.com", "password": "short"})
    assert res.status_code == 422


async def test_duplicate_email_conflicts(client, make_client, signup):
    await signup(client, "a@example.com")
    async with make_client() as other:
        res = await other.post(
            "/v1/auth/signup", json={"email": "A@example.com", "password": "another long pass"}
        )
        assert res.status_code == 409


async def test_first_user_owner_then_member_then_closed(owner, make_client, signup):  # MVP AC-2
    assert (await owner.get("/v1/me")).json()["role"] == "owner"
    async with make_client() as second:
        assert (await signup(second, "second@example.com"))["role"] == "member"
        res = await second.patch("/v1/settings", json={"open_signup": False})
        assert res.status_code == 403  # members cannot close sign-up

    res = await owner.patch("/v1/settings", json={"open_signup": False})
    assert res.json()["open_signup"] is False
    async with make_client() as third:
        res = await third.post(
            "/v1/auth/signup", json={"email": "third@example.com", "password": "long enough pass"}
        )
        assert res.status_code == 403


async def test_sixth_failed_signin_is_rate_limited(client, make_client, signup):  # MVP AC-3
    await signup(client, "ana@example.com")
    await client.post("/v1/auth/logout")
    creds = {"email": "ana@example.com", "password": "wrong password!!"}
    for _ in range(5):
        assert (await client.post("/v1/auth/login", json=creds)).status_code == 401
    assert (await client.post("/v1/auth/login", json=creds)).status_code == 429
    creds["password"] = "correct horse battery"
    assert (await client.post("/v1/auth/login", json=creds)).status_code == 429


async def test_foreign_origin_rejected(owner, make_client, signup):  # MVP AC-3
    res = await owner.patch(
        "/v1/settings", json={"open_signup": False}, headers={"origin": "https://evil.test"}
    )
    assert res.status_code == 403
    res = await owner.patch(
        "/v1/settings", content="open_signup=false", headers={"content-type": "text/plain"}
    )
    assert res.status_code == 415


async def test_unauthenticated_requests_get_401(client, make_client, signup):
    assert (await client.get("/v1/me")).status_code == 401
    assert (await client.get("/v1/settings")).status_code == 401
