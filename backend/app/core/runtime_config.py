from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.secrets import SecretConfigurationError, get_scalar_secret


def validate_paystack_key_prefix(*, environment: str, secret_key: str, public_key: str) -> None:
    expected_secret = "sk_live_" if environment in {"prod", "production"} else "sk_test_"
    expected_public = "pk_live_" if environment in {"prod", "production"} else "pk_test_"
    if not secret_key.startswith(expected_secret):
        raise SecretConfigurationError(
            f"Paystack secret-key environment mismatch: {environment} requires {expected_secret}"
        )
    if not public_key.startswith(expected_public):
        raise SecretConfigurationError(
            f"Paystack public-key environment mismatch: {environment} requires {expected_public}"
        )


def validate_runtime_configuration(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.ENVIRONMENT not in {"staging", "prod", "production"}:
        return
    if not settings.PAYSTACK_SECRET_KEY_ARN or not settings.PAYSTACK_PUBLIC_KEY_ARN:
        raise SecretConfigurationError(
            "Managed Paystack secret and public key ARNs are required in deployed environments"
        )
    validate_paystack_key_prefix(
        environment=settings.ENVIRONMENT,
        secret_key=get_scalar_secret(settings.PAYSTACK_SECRET_KEY_ARN),
        public_key=get_scalar_secret(settings.PAYSTACK_PUBLIC_KEY_ARN),
    )
