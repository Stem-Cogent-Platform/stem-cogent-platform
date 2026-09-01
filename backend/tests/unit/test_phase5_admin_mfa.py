import pytest

from app.api.v1.admin import router as admin_router
from app.authn.totp import verify_totp
from app.ops import grant_system_admin


class GrantResult:
    def __init__(self, row=None) -> None:
        self.row = row

    def mappings(self) -> "GrantResult":
        return self

    def one_or_none(self):
        return self.row


class GrantConnection:
    def __init__(self, identity) -> None:
        self.results = [GrantResult(identity), GrantResult(), GrantResult(), GrantResult(), GrantResult()]
        self.statements: list[str] = []

    async def execute(self, statement, parameters=None) -> GrantResult:
        self.statements.append(str(statement))
        return self.results.pop(0)


class GrantEngine:
    def __init__(self, connection: GrantConnection) -> None:
        self.connection = connection

    def begin(self):
        connection = self.connection

        class Transaction:
            async def __aenter__(self):
                return connection

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        return Transaction()


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


@pytest.mark.asyncio
async def test_system_admin_grant_is_scoped_audited_and_closes_database(monkeypatch) -> None:
    from unittest.mock import AsyncMock
    from uuid import uuid4

    identity = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "permission_role": "ADMIN",
        "tenant_name": "Stem Internal Operations",
    }
    connection = GrantConnection(identity)
    close = AsyncMock()
    monkeypatch.setattr(grant_system_admin, "get_engine", lambda: GrantEngine(connection))
    monkeypatch.setattr(grant_system_admin, "close_database_connection", close)

    result = await grant_system_admin.grant(
        " Operator@Example.com ",
        "stem internal operations",
        "operator@example.com",
    )

    assert result == {"status": "granted", "tenant_name": "Stem Internal Operations"}
    assert any("SYSTEM_ADMIN_GRANTED" in statement for statement in connection.statements)
    assert any("CAST(:previous_role AS TEXT)" in statement for statement in connection.statements)
    assert any("permission_role='SYSTEM_ADMIN'" in statement for statement in connection.statements)
    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_system_admin_grant_rejects_missing_database_and_identity(monkeypatch) -> None:
    monkeypatch.setattr(grant_system_admin, "get_engine", lambda: None)
    with pytest.raises(RuntimeError, match="not configured"):
        await grant_system_admin.grant("operator@example.com", "Ops", "operator@example.com")

    connection = GrantConnection(None)
    monkeypatch.setattr(grant_system_admin, "get_engine", lambda: GrantEngine(connection))
    with pytest.raises(RuntimeError, match="not found"):
        await grant_system_admin.grant("operator@example.com", "Ops", "operator@example.com")


def test_system_admin_cli_forwards_all_explicit_confirmations(monkeypatch, capsys) -> None:
    import sys

    async def fake_grant(email, expected_tenant, confirmed_email):
        assert (email, expected_tenant, confirmed_email) == (
            "operator@example.com",
            "Ops",
            "operator@example.com",
        )
        return {"status": "granted"}

    monkeypatch.setattr(grant_system_admin, "grant", fake_grant)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "grant-system-admin",
            "--email",
            "operator@example.com",
            "--expected-tenant",
            "Ops",
            "--confirm-email",
            "operator@example.com",
        ],
    )
    grant_system_admin.main()
    assert capsys.readouterr().out.strip() == '{"status": "granted"}'
