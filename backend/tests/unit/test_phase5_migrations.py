from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
VERSIONS = BACKEND_ROOT / "alembic" / "versions"


def _offline_sql(start: str, end: str) -> str:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost/db"
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", f"{start}:{end}", "--sql"],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_phase5_migration_chain_and_security_contracts() -> None:
    invite = (VERSIONS / "0023_2026_08_31_phase5_pilot_invites_and_activation.py").read_text()
    lifecycle = (VERSIONS / "0024_2026_08_31_phase5_brief_lifecycle_and_paths.py").read_text()
    events = (VERSIONS / "0025_2026_08_31_phase5_product_events.py").read_text()

    assert 'down_revision: str | None = "0022"' in invite
    assert 'down_revision: str | None = "0023"' in lifecycle
    assert 'down_revision: str | None = "0024"' in events
    assert "token_hash TEXT NOT NULL UNIQUE" in invite
    assert "SECURITY DEFINER" in invite
    assert "current_setting('app.system_admin', true) = 'true'" in invite
    assert "lookback_days BETWEEN 30 AND 60" in invite
    assert "UNIQUE NULLS NOT DISTINCT" in invite
    assert "ALTER TABLE decision.brief_events FORCE ROW LEVEL SECURITY" in lifecycle
    assert "material_change_count" in lifecycle
    assert "response_options JSONB" in lifecycle
    assert "ALTER TABLE feedback.product_events FORCE ROW LEVEL SECURITY" in events
    assert "REVOKE UPDATE, DELETE, TRUNCATE" in events


def test_phase5_migrations_render_offline() -> None:
    sql = _offline_sql("0022", "0025")

    assert "CREATE TABLE auth.tenant_invitations" in sql
    assert "CREATE TABLE context.activation_runs" in sql
    assert "CREATE TABLE decision.brief_events" in sql
    assert "CREATE TABLE feedback.product_events" in sql
    assert "-- Running upgrade 0024 -> 0025" in sql
