from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.workers.tasks import pilot_activation


class Result:
    def __init__(self, *, row=None, rows=None, scalar=None) -> None:
        self.row = row
        self.rows = [] if rows is None else rows
        self.scalar = scalar

    def mappings(self) -> "Result":
        return self

    def one(self):
        return self.row

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.scalar


class Session:
    def __init__(self, *results: Result) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.commits = 0

    async def execute(self, statement, parameters=None) -> Result:
        self.statements.append(str(statement))
        return self.results.pop(0)

    async def commit(self) -> None:
        self.commits += 1


def session_source(session: Session):
    async def source():
        yield session

    return source


@pytest.mark.asyncio
async def test_ready_user_starts_exact_21_day_trial(monkeypatch) -> None:
    tenant_id, user_id, engagement_id = uuid4(), uuid4(), uuid4()
    session = Session(
        Result(),
        Result(row={"accepted": True, "lens": True, "focus": True, "first_value": True}),
        Result(scalar=engagement_id),
        Result(),
        Result(),
        Result(),
        Result(),
        Result(),
    )
    monkeypatch.setattr(pilot_activation, "get_session", session_source(session))

    await pilot_activation._maybe_start_trial(tenant_id, user_id)

    assert session.commits == 1
    assert sum("pilot.checkpoints" in statement for statement in session.statements) == 3
    assert any("PILOT_ACTIVATED" in statement for statement in session.statements)


@pytest.mark.asyncio
async def test_incomplete_or_started_pilot_is_not_restarted(monkeypatch) -> None:
    tenant_id, user_id = uuid4(), uuid4()
    incomplete = Session(
        Result(),
        Result(row={"accepted": True, "lens": False, "focus": True, "first_value": True}),
    )
    monkeypatch.setattr(pilot_activation, "get_session", session_source(incomplete))
    await pilot_activation._maybe_start_trial(tenant_id, user_id)
    assert incomplete.commits == 0

    started = Session(
        Result(),
        Result(row={"accepted": True, "lens": True, "focus": True, "first_value": True}),
        Result(scalar=None),
    )
    monkeypatch.setattr(pilot_activation, "get_session", session_source(started))
    await pilot_activation._maybe_start_trial(tenant_id, user_id)
    assert started.commits == 0


@pytest.mark.asyncio
async def test_personalisation_rebuilds_each_output_then_checks_readiness(monkeypatch) -> None:
    tenant_id, user_id = uuid4(), uuid4()
    outputs = [
        {"global_output_id": uuid4(), "signal_id": uuid4()},
        {"global_output_id": uuid4(), "signal_id": uuid4()},
    ]
    session = Session(Result(), Result(rows=outputs))
    decide = AsyncMock(return_value="created")
    readiness = AsyncMock()
    monkeypatch.setattr(pilot_activation, "get_session", session_source(session))
    monkeypatch.setattr(pilot_activation, "run_decision_briefs", decide)
    monkeypatch.setattr(pilot_activation, "_maybe_start_trial", readiness)

    result = await pilot_activation.personalise_user(
        {"tenant_id": str(tenant_id), "user_id": str(user_id)}
    )

    assert result == "PERSONALISED:2"
    assert decide.await_count == 2
    readiness.assert_awaited_once_with(tenant_id, user_id)


@pytest.mark.asyncio
async def test_failure_and_completion_helpers_persist_bounded_events(monkeypatch) -> None:
    tenant_id, run_id = uuid4(), uuid4()
    session = Session(Result())
    await pilot_activation._finish_failed(session, run_id, tenant_id, "x" * 2000)
    assert session.commits == 1

    published: dict = {}

    class Publisher:
        def __init__(self, app) -> None:
            self.app = app

        async def publish(self, queue_url, event) -> None:
            published.update(queue_url=queue_url, event=event)

    monkeypatch.setattr(pilot_activation, "CeleryEventPublisher", Publisher)
    monkeypatch.setattr(
        pilot_activation,
        "get_settings",
        lambda: SimpleNamespace(SQS_PIPELINE_RECOMMENDED_URL="https://sqs.example/recommended"),
    )
    await pilot_activation._publish_completed(
        run_id,
        tenant_id,
        {"assessments": 4, "company_briefs": 2, "monitoring": 3},
    )
    assert published["event"]["event_type"] == "ACTIVATION_COMPLETED"
    assert published["event"]["payload"]["company_briefs_created"] == 2

    monkeypatch.setattr(
        pilot_activation,
        "get_settings",
        lambda: SimpleNamespace(SQS_PIPELINE_RECOMMENDED_URL=""),
    )
    with pytest.raises(RuntimeError, match="not configured"):
        await pilot_activation._publish_completed(run_id, tenant_id, {})


def test_celery_entrypoints_delegate_and_acknowledge(monkeypatch) -> None:
    monkeypatch.setattr(pilot_activation, "run_async_worker", lambda callback: "delegated")
    assert pilot_activation.activate_pilot({}) == "delegated"
    assert pilot_activation.personalise_pilot_user({}) == "delegated"
    assert pilot_activation.activation_completed({}) == "ACKNOWLEDGED"
