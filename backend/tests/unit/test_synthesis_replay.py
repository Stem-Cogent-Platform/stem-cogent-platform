from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.workers.tasks import synthesis


@pytest.mark.asyncio
@pytest.mark.parametrize("duplicate", [False, True])
@pytest.mark.parametrize("failed", [False, True])
async def test_replay_checks_committed_identity_before_provider(monkeypatch, duplicate, failed):
    signal_id, output_id = uuid4(), uuid4()
    statements = []

    async def execute(statement, parameters):
        statements.append(str(statement))
        if len(statements) == 1:
            assert "pg_advisory_xact_lock" in str(statement)
            assert "global_outputs" not in str(statement)
            return None
        if len(statements) == 2:
            return SimpleNamespace(scalar_one_or_none=lambda: uuid4() if duplicate else None)
        return SimpleNamespace(
            mappings=lambda: SimpleNamespace(
                one_or_none=lambda: {"id": output_id, "llm_synthesis_failed": failed}
            )
        )

    async def sessions():
        yield SimpleNamespace(execute=execute)

    def forbidden_provider():
        pytest.fail("Replay must not construct a paid provider client")

    publish = AsyncMock()
    monkeypatch.setattr(synthesis, "get_session", sessions)
    monkeypatch.setattr(synthesis, "_synthesis_client", forbidden_provider)
    monkeypatch.setattr(synthesis, "_publish_synthesized", publish)
    result = await synthesis.run_synthesis({"payload": {"signal_id": str(signal_id)}})
    assert result == ("DUPLICATE_SKIPPED" if duplicate else "ALREADY_SYNTHESIZED")
    assert publish.await_count == (0 if duplicate else 1)
    assert len(statements) == (2 if duplicate else 3)


@pytest.mark.asyncio
async def test_explicit_failed_recovery_calls_generation_once(monkeypatch):
    signal_id, output_id = uuid4(), uuid4()
    execute = AsyncMock(side_effect=[None,
        SimpleNamespace(scalar_one_or_none=lambda: None),
        SimpleNamespace(mappings=lambda: SimpleNamespace(one_or_none=lambda: {
            "id": output_id, "llm_synthesis_failed": True,
        })),
    ])
    session = SimpleNamespace(execute=execute, commit=AsyncMock())
    async def sessions():
        yield session
    client = SimpleNamespace(model="configured-model", last_provider="openai", aclose=AsyncMock())
    generate = AsyncMock(return_value=(object(), False))
    monkeypatch.setattr(synthesis, "get_session", sessions)
    monkeypatch.setattr(synthesis, "_assemble_context", AsyncMock(return_value=object()))
    monkeypatch.setattr(synthesis, "_synthesis_client", lambda: client)
    monkeypatch.setattr(synthesis, "SynthesisService", lambda _: SimpleNamespace(synthesize=generate))
    monkeypatch.setattr(synthesis, "_persist_output", AsyncMock(return_value=output_id))
    monkeypatch.setattr(synthesis, "_publish_synthesized", AsyncMock())
    result = await synthesis.run_synthesis({"payload": {"signal_id": str(signal_id)}}, retry_failed=True)
    assert result == "SYNTHESIZED"
    generate.assert_awaited_once()
    session.commit.assert_awaited_once()
    client.aclose.assert_awaited_once()
