import pytest

from app.api.v1.admin import router as admin_router
from app.authn.totp import verify_totp
from app.ops import grant_system_admin


def test_rfc6238_verifier_accepts_valid_code_in_bounded_window() -> None:
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    assert verify_totp(secret, "406058", at_time=1_700_000_000)
    assert verify_totp(secret, "406058", at_time=1_700_000_029)


def test_rfc6238_verifier_rejects_malformed_or_wrong_codes() -> None:
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    assert not verify_totp(secret, "12345", at_time=1_700_000_000)
    assert not verify_totp(secret, "000000", at_time=1_700_000_000)
    assert not verify_totp("invalid", "123456", at_time=1_700_000_000)


def test_internal_admin_api_uses_versioned_private_route() -> None:
    paths = {route.path for route in admin_router.routes}
    assert "/api/v1/internal/admin/tenants" in paths
    assert "/internal/admin/tenants" not in paths


@pytest.mark.asyncio
async def test_system_admin_grant_requires_exact_email_confirmation(monkeypatch) -> None:
    monkeypatch.setattr(
        grant_system_admin,
        "get_engine",
        lambda: pytest.fail("database must not be opened before confirmation"),
    )
    with pytest.raises(ValueError, match="exactly match"):
        await grant_system_admin.grant(
            "operator@example.com",
            "Odion Alex",
            "different@example.com",
        )
