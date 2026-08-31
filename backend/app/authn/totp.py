"""Small RFC 6238 verifier for the separate system-administrator factor."""

from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time


def verify_totp(secret: str, supplied_code: str, *, at_time: int | None = None) -> bool:
    code = "".join(supplied_code.split())
    if len(code) != 6 or not code.isdigit():
        return False
    normalized = "".join(secret.split()).upper()
    try:
        key = base64.b32decode(normalized + "=" * (-len(normalized) % 8), casefold=True)
    except (ValueError, TypeError):
        return False
    if len(key) < 16:
        return False
    timestamp = int(time.time() if at_time is None else at_time)
    return any(
        hmac.compare_digest(_hotp(key, timestamp // 30 + offset), code)
        for offset in (-1, 0, 1)
    )


def _hotp(key: bytes, counter: int) -> str:
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"
