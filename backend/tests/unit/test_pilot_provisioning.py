from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.authn import provision_pilot


class Result:
    def __init__(self, scalar=None) -> None:
        self.scalar = scalar

    def scalar_one(self):
        assert self.scalar is not None
        return self.scalar


class Session:
    def __init__(self, *results: Result) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.commits = 0

    async def execute(self, statement, parameters=None) -> Result:
        self.statements.append(str(statement))
        assert self.results, f"Unexpected SQL execution: {statement}"
        return self.results.pop(0)

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_provision_creates_an_invite_only_trial_and_checkpoint_schedule(
    monkeypatch,
) -> None:
    tenant_id, user_id, engagement_id = uuid4(), uuid4(), uuid4()
    session = Session(
        Result(),
        Result(),
        Result(scalar=user_id),
        Result(),
        Result(),
        Result(scalar=engagement_id),
        Result(),
        Result(),
        Result(),
    )

    async def sessions():
        yield session

    args = SimpleNamespace(
        workspace_id=tenant_id,
        workspace_name="Odion Alex",
        workspace_slug="odion-alex-pilot",
        email="MarcoAlex201804@Gmail.com",
        display_name="Odion Alex",
        password_secret_arn="arn:pilot-password",
        cohort_code="GUIDED_PILOT_2026_08",
    )
    monkeypatch.setattr(
        provision_pilot,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="production"),
    )
    monkeypatch.setattr(
        provision_pilot, "get_scalar_secret", lambda _arn: "safe-pilot-password"
    )
    monkeypatch.setattr(
        provision_pilot, "hash_password", lambda password: f"hash:{password}"
    )
    monkeypatch.setattr(provision_pilot, "get_session", sessions)
    result = await provision_pilot.provision(args)
    assert result == {
        "workspace_id": str(tenant_id),
        "email": "marcoalex201804@gmail.com",
        "pilot_status": "ACTIVE",
    }
    assert session.commits == 1
    assert (
        sum("pilot.checkpoints" in statement for statement in session.statements) == 3
    )
    assert any("billing.subscriptions" in statement for statement in session.statements)


@pytest.mark.asyncio
async def test_provision_rejects_unsafe_environment_before_resolving_a_password(
    monkeypatch,
) -> None:
    args = SimpleNamespace(
        workspace_id=uuid4(),
        workspace_name="Odion Alex",
        workspace_slug="odion-alex-pilot",
        email="marcoalex201804@gmail.com",
        display_name="Odion Alex",
        password_secret_arn="arn:pilot-password",
        cohort_code="GUIDED_PILOT_2026_08",
    )
    monkeypatch.setattr(
        provision_pilot,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="development"),
    )
    with pytest.raises(RuntimeError, match="deployed environments"):
        await provision_pilot.provision(args)
