from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

import bcrypt

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000


def validate_password_complexity(password: str) -> None:
    """Validate enterprise password complexity requirements.

    Requirements:
    - Minimum 8 characters, maximum 256 characters
    - At least 1 uppercase letter
    - At least 1 number
    """
    if len(password) < 8 or len(password) > 256:
        raise ValueError("Password must be between 8 and 256 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least 1 uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least 1 number")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Hash password using standard bcrypt or legacy PBKDF2 when explicit salt provided."""
    if salt is not None:
        if len(password) < 12 or len(password) > 256:
            raise ValueError("Password must contain between 12 and 256 characters")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
        return "$".join(
            (
                _ALGORITHM,
                str(_ITERATIONS),
                base64.urlsafe_b64encode(salt).decode().rstrip("="),
                base64.urlsafe_b64encode(digest).decode().rstrip("="),
            )
        )

    validate_password_complexity(password)
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, encoded: str | None) -> bool:
    """Verify password against bcrypt hash or legacy PBKDF2 hash."""
    if not encoded:
        return False

    if encoded.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            pw_bytes = password.encode("utf-8")[:72]
            return bcrypt.checkpw(pw_bytes, encoded.encode("utf-8"))
        except (ValueError, TypeError):
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
