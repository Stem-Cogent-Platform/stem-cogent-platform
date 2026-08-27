from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 12 or len(password) > 256:
        raise ValueError("Password must contain between 12 and 256 characters")
    salt = salt or secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return "$".join(
        (
            _ALGORITHM,
            str(_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode().rstrip("="),
            base64.urlsafe_b64encode(digest).decode().rstrip("="),
        )
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = encoded.split("$", 3)
        iterations = int(raw_iterations)
        if algorithm != _ALGORITHM or iterations < 310_000 or iterations > 1_000_000:
            return False
        salt = _decode(raw_salt)
        expected = _decode(raw_digest)
        supplied = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, supplied)


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
