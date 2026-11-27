"""AES-GCM encryption for stored secrets (ADR-0019). The key comes from OVAS_SECRET_KEY."""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from ovas_api.config import get_settings


def _key() -> bytes:
    secret = get_settings().secret_key
    if not secret:
        raise HTTPException(400, "Set OVAS_SECRET_KEY on the server before storing secrets.")
    return hashlib.sha256(secret.encode()).digest()


def encrypt(plaintext: str) -> str:
    nonce = os.urandom(12)
    return base64.b64encode(
        nonce + AESGCM(_key()).encrypt(nonce, plaintext.encode(), None)
    ).decode()


def decrypt(token: str) -> str:
    raw = base64.b64decode(token)
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode()
