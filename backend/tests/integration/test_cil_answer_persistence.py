from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.api.v1 import cil
from app.cil import answering
from app.core.config import get_settings
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize('invalid_field', ['answer_text', 'follow_up_suggestions'])
async def test_invalid_provider_text_uses_persistable_cited_fallback(pilot, monkeypatch, invalid_field):  # noqa: F811
    ctx, base = pilot
    value = await add_value(pilot)
    ctx.principal = replace(ctx.principal, permissions=ctx.principal.permissions | {'USE_CIL'})
    monkeypatch.setattr(cil, 'require_feature', lambda *_: None)
    monkeypatch.setattr(cil, '_enforce_rate_limit', AsyncMock())
    monkeypatch.setattr(get_settings(), 'CIL_ENABLED', True)
    monkeypatch.setattr(get_settings(), 'OPENAI_API_KEY_ARN', 'local-provider-fixture')
    client = AsyncMock()
    raw = {'answer_text': 'A source-backed local fixture.',
           'cited_signal_ids': [str(value['signal_id'])], 'follow_up_suggestions': ['What remains uncertain?']}
    raw[invalid_field] = 'Invalid\x00provider text' if invalid_field == 'answer_text' else ['Invalid\x00suggestion']
    client.generate.return_value = raw
    monkeypatch.setattr(answering, 'build_generation_client', lambda **_: client)
    response = await cil.query_cil(cil.CILQuery(query='What changed?', anchor_type='SIGNAL', anchor_id=value['signal_id']), ctx)
    assert response.response_grounded
    assert '\x00' not in response.answer_text
    assert response.citations[0]['source_signal_id'] == str(value['signal_id'])
    row = (await ctx.session.execute(text('SELECT response_text,provider FROM cil.query_log WHERE tenant_id=:tenant AND session_id=:session'), {'tenant': base['tenant_id'], 'session': response.session_id})).mappings().one()
    assert row['provider'] == 'deterministic'
    assert row['response_text'] == response.answer_text
    client.generate.assert_awaited_once()
    client.aclose.assert_awaited_once()
