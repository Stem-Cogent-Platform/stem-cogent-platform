from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.workers.tasks import embedding


@pytest.mark.parametrize('days', [0, 61])
def test_paid_processing_window_rejects_unbounded_configuration(days):
    with pytest.raises(ValidationError):
        Settings(PIPELINE_RECENT_LOOKBACK_DAYS=days)


@pytest.mark.asyncio
@pytest.mark.parametrize('age,expected', [(13, 'CONTEXT_READY'), (15, 'SKIPPED:HISTORICAL')])
async def test_recovery_window_gates_paid_work_and_downstream_publication(monkeypatch, age, expected):
    monkeypatch.setattr(get_settings(), 'PIPELINE_RECENT_LOOKBACK_DAYS', 14)
    session = AsyncMock()

    async def sessions():
        yield session

    monkeypatch.setattr(embedding, 'get_session', sessions)
    monkeypatch.setattr(embedding, '_load_scored_signal', AsyncMock(return_value={
        'published_at': datetime.now(UTC)-timedelta(days=age), 'processing_flags': [],
        'title': 'Dated evidence', 'body_text': 'Source evidence', 'primary_domain': 'REGULATORY_POLICY',
        'entity_labels': [], 'entity_ids': [],
    }))
    cache = AsyncMock(return_value=(0.1, 0.2))
    persist, publish = AsyncMock(), AsyncMock()
    monkeypatch.setattr(embedding, '_cached_embedding', cache)
    monkeypatch.setattr(embedding, '_persist_embedding', persist)
    monkeypatch.setattr(embedding, 'find_similar_signals', AsyncMock(return_value=()))
    monkeypatch.setattr(embedding, '_assign_cluster', AsyncMock(return_value=None))
    monkeypatch.setattr(embedding, '_publish_context_ready', publish)
    result = await embedding.run_embedding({'payload': {'signal_id': str(uuid4())}})
    assert result == expected
    if age > 14:
        cache.assert_not_awaited()
        persist.assert_not_awaited()
        publish.assert_not_awaited()
    else:
        cache.assert_awaited_once()
        persist.assert_awaited_once()
        publish.assert_awaited_once()
