"""Transactional authentication email delivery; never simulate acceptance."""

import httpx

from app.core.config import get_settings
from app.core.secrets import get_scalar_secret


async def send_login_code(email: str, code: str) -> None:
    settings = get_settings()
    if not settings.RESEND_API_KEY_ARN or not settings.AUTH_EMAIL_FROM:
        raise RuntimeError("Authentication email delivery is not configured")
    key = get_scalar_secret(settings.RESEND_API_KEY_ARN)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "from": settings.AUTH_EMAIL_FROM,
                "to": [email],
                "subject": "Your Stem Cogent sign-in code",
                "text": f"Your sign-in code is {code}. It expires in 15 minutes. "
                        "If you did not request this code, ignore this email.",
            },
        )
        response.raise_for_status()
        if not response.json().get("id"):
            raise RuntimeError("Email provider did not acknowledge delivery")
