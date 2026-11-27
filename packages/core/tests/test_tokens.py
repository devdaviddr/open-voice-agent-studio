from ovas_core.tokens import sign_session, verify_session


def test_round_trip_and_tamper():
    token = sign_session("abc", "k")
    assert verify_session(token, "k") == "abc"
    assert verify_session(token, "other") is None
    assert verify_session(token.replace("abc", "abd"), "k") is None
    assert verify_session("garbage", "k") is None


def test_expired():
    assert verify_session(sign_session("abc", "k", ttl_seconds=-1), "k") is None
