from datetime import UTC, datetime

from app.workers.scheduler_service import seconds_to_next_minute


def test_scheduler_aligns_ticks_to_utc_minute_boundaries() -> None:
    assert seconds_to_next_minute(
        datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC)
    ) == 60.0
    assert seconds_to_next_minute(
        datetime(2026, 8, 19, 12, 0, 42, 500000, tzinfo=UTC)
    ) == 17.5
