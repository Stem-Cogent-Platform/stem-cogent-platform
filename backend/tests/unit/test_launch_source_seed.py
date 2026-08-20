from __future__ import annotations

import importlib.util
import runpy
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

from app.workers.scheduler import cron_matches


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = BACKEND_ROOT / "alembic" / "data" / "launch_sources_v1.py"
SEED_PATH = BACKEND_ROOT / "alembic" / "seeds" / "seed_launch_sources.py"


def _load_seed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_launch_source_seed", SEED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_covers_launch_collectors_and_all_taxonomy_domains() -> None:
    data = runpy.run_path(DATA_PATH)
    sources = data["LAUNCH_SOURCES"]

    assert data["MANIFEST_VERSION"] == "2026.08-v3"
    assert len(sources) == 17
    assert {source.source_type for source in sources} == {
        "RSS",
        "API",
        "HTML",
        "PDF",
        "USER_UPLOAD",
        "LIVE_SEARCH",
    }
    assert {domain for source in sources for domain in source.coverage_domains} == data[
        "TAXONOMY_DOMAINS"
    ]
    assert len({source.source_code for source in sources}) == len(sources)


def test_external_sources_are_official_https_endpoints_with_review_evidence() -> None:
    sources = runpy.run_path(DATA_PATH)["LAUNCH_SOURCES"]
    external = [source for source in sources if source.source_type != "USER_UPLOAD"]
    approved_hosts = {
        "www.cbn.gov.ng",
        "sec.gov.ng",
        "status.paystack.com",
        "status.flutterwave.com",
        "ndpc.gov.ng",
        "nibss-plc.com.ng",
        "flutterwave.com",
        "moniepoint.com",
        "techcabal.com",
        "disruptafrica.com",
        "technext24.com",
        "businessday.ng",
        "www.nigerianstat.gov.ng",
        "api.gdeltproject.org",
    }

    assert {urlsplit(source.base_url).hostname for source in external} == approved_hosts
    assert all(urlsplit(source.base_url).scheme == "https" for source in external)
    assert all(source.review_reference for source in sources)
    assert all(0.75 <= source.reliability_score <= 1.0 for source in sources)


def test_broad_sources_can_surface_the_whole_priority_fintech_manifest() -> None:
    source_data = runpy.run_path(DATA_PATH)
    registry_data = runpy.run_path(
        BACKEND_ROOT / "alembic" / "data" / "launch_registry_v2.py"
    )
    broad_sources = {
        "TECHCABAL_RSS",
        "DISRUPT_AFRICA_RSS",
        "TECHNEXT_RSS",
        "BUSINESSDAY_TECH_RSS",
        "GDELT_NIGERIA_DISCOVERY",
    }

    assert broad_sources <= {
        source.source_code for source in source_data["LAUNCH_SOURCES"]
    }
    assert len(registry_data["PRIORITY_FINTECH_MANIFEST"]) == 100
    assert len({row[1] for row in registry_data["PRIORITY_FINTECH_MANIFEST"]}) == 9


def test_schedules_are_reviewed_utc_cron_and_static_sources_are_manual() -> None:
    sources = runpy.run_path(DATA_PATH)["LAUNCH_SOURCES"]
    scheduled = [source for source in sources if source.schedule_cron]
    manual = [source for source in sources if not source.schedule_cron]

    assert {source.source_type for source in manual} == {"PDF", "USER_UPLOAD"}
    assert all(len(source.schedule_cron.split()) == 5 for source in scheduled)
    # Parsing is the contract: matching need not be true for this arbitrary instant.
    for source in scheduled:
        cron_matches(source.schedule_cron, datetime.now(UTC))


def test_seed_is_idempotent_non_destructive_and_verifies_exact_managed_rows() -> None:
    module = _load_seed_module()
    sql = str(module._UPSERT)
    source = SEED_PATH.read_text(encoding="utf-8")

    assert "ON CONFLICT (source_code) DO UPDATE" in sql
    assert "DELETE" not in sql
    assert "last_successful_collect" not in sql
    assert "actual != expected" in source
    assert "manifest_version" in source
    assert "health_status = 'INACTIVE'" in str(module._RETIRE_SUPERSEDED)


def test_seed_cli_imports_from_repository_root() -> None:
    probe = (
        "import importlib.util; "
        f"p={str(SEED_PATH)!r}; "
        "s=importlib.util.spec_from_file_location('source_seed_probe', p); "
        "m=importlib.util.module_from_spec(s); "
        "s.loader.exec_module(m); "
        "assert m.BACKEND_ROOT.name == 'backend'"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=BACKEND_ROOT.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
