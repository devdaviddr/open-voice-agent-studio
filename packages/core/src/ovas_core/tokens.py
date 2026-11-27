"""Short-lived signed session tokens shared by the API (issuer) and the runtime (verifier)."""

import hashlib
import hmac
import time


def sign_session(session_id: str, key: str, ttl_seconds: int = 300) -> str:
    expires = int(time.time()) + ttl_seconds
    body = f"{session_id}.{expires}"
    mac = hmac.new(key.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{mac}"


def verify_session(token: str, key: str) -> str | None:
    """Return the session ID if the token is genuine and unexpired, else None."""
    try:
        session_id, expires, mac = token.rsplit(".", 2)
        expected = hmac.new(key.encode(), f"{session_id}.{expires}".encode(), hashlib.sha256)
        if not hmac.compare_digest(mac, expected.hexdigest()) or int(expires) < time.time():
            return None
    except ValueError:
        return None
    return session_id
