from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    password_hash = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"{_base64url_encode(salt)}:{_base64url_encode(password_hash)}"


def verify_password(password: str, stored_password: str) -> bool:
    parts = stored_password.split(":", 1)
    if len(parts) != 2:
        return False
    salt = _base64url_decode(parts[0])
    expected = _base64url_decode(parts[1])
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return hmac.compare_digest(actual, expected)


def create_access_token(payload: dict[str, Any], secret_key: str, expires_in_seconds: int = 60 * 60 * 24) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    body = {**payload, "iat": now, "exp": now + expires_in_seconds}
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret_key.encode("utf-8"), f"{encoded_header}.{encoded_payload}".encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str, secret_key: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    encoded_header, encoded_payload, encoded_signature = parts
    expected = hmac.new(secret_key.encode("utf-8"), f"{encoded_header}.{encoded_payload}".encode("ascii"), hashlib.sha256).digest()
    try:
        actual = _base64url_decode(encoded_signature)
        payload = json.loads(_base64url_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if not hmac.compare_digest(actual, expected):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
