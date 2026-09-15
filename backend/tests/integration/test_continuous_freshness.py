# ruff: noqa: F811
"""Source age governs shared delivery for every eligible active user."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.workers.tasks import decision
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("age,expected", [(1, 3), (90, 0), (None, 0), (-1, 0)])
async def test_global_delivery_preserves_source_age_for_all_active_lenses(pilot, monkeypatch, age, expected):
    ctx, base = pilot
    value = await add_value(pilot, age=age)
    second_user = uuid4()
    await ctx.session.execute(text("""
        INSERT INTO auth.users(id,tenant_id,email,permission_role,onboarding_completed_at)
        VALUES (:id,:tenant_id,:email,'ADMIN',NOW())
    """), {"id": second_user, "tenant_id": base["tenant_id"], "email": f"{second_user}@example.invalid"})
    await ctx.session.execute(text("""
        INSERT INTO context.user_decision_lenses(tenant_id,user_id,role_code)
        VALUES (:tenant_id,:id,'CEO')
    """), {"id": second_user, "tenant_id": base["tenant_id"]})
    await ctx.session.execute(text("""
        UPDATE context.company_objects SET name='Grey',object_type='COMPETITOR'
        WHERE tenant_id=:tenant_id AND id=:object_id
    """), base)
    await ctx.session.execute(text("""
        UPDATE pipeline.signals SET title='Grey launches a cross-border payment corridor',
          body_text='Grey reports a new payment corridor.', primary_domain='MARKET_EXPANSION',
          subcategory_tags=ARRAY['CROSS_BORDER_PRODUCT_EXPANSION']
        WHERE id=:signal_id
    """), value)
    # Production messages refer to already committed source records.
    await ctx.session.commit()
    async def sessions():
        yield ctx.session
    monkeypatch.setattr(decision, 'get_session', sessions)
    published = AsyncMock()
    monkeypatch.setattr(decision, '_publish_ready', published)
    # No tenant or user override: exercise the shared active-tenant inventory.
    event = {'payload': {'signal_id': str(value['signal_id']), 'global_output_id': str(value['output_id'])}}
    assert await decision.run_decision_briefs(event) == f'CREATED:{expected}'
    await ctx.session.execute(text("SELECT set_config('app.current_tenant_id',:id,true)"), {'id': str(base['tenant_id'])})
    rows = (await ctx.session.execute(text("""
        SELECT id,user_id FROM decision.briefs WHERE tenant_id=:tenant_id AND signal_id=:signal_id
    """), value)).mappings().all()
    assert len(rows) == expected
    if expected:
        assert {row['user_id'] for row in rows} == {None, base['user_id'], second_user}
    assert published.await_count == expected
    assert await decision.run_decision_briefs(event) == 'CREATED:0'
    assert published.await_count == expected
    # Synthesis/collection happen now in this fixture. Publication must stay untouched.
    actual = (await ctx.session.execute(text('SELECT published_at FROM pipeline.signals WHERE id=:signal_id'), value)).scalar_one()
    assert actual == value['published']


@pytest.mark.parametrize("days", [90, None, -1])
async def test_stale_undated_or_future_source_cannot_be_delivered_by_replay(pilot, monkeypatch, days):
    from datetime import UTC, datetime, timedelta
    from app.api.v1 import product
    from app.workers.tasks import delivery
    from tests.integration.test_delivery_preferences import setup_delivery
    ctx, event = await setup_delivery(pilot, monkeypatch)
    published_at = None if days is None else datetime.now(UTC) - timedelta(days=days)
    await ctx.session.execute(text("""
        UPDATE pipeline.signals SET published_at=:published_at
        WHERE id=(SELECT signal_id FROM decision.briefs WHERE id=:id)
    """), {'published_at': published_at, 'id': event['payload']['brief_id']})
    assert await delivery.run_decision_brief_delivery(event) == 'SKIPPED:SOURCE_NOT_CURRENT'
    assert await product.list_alerts(ctx) == []
    assert await product.list_digests(ctx) == []
    delivery._publish.assert_not_awaited()
