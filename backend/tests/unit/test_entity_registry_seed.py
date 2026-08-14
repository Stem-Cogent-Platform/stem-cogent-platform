import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "infrastructure" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from entity_registry_seed_data import (  # noqa: E402
    ENTITY_SEEDS,
    ENTITY_TYPES,
    NIGERIA_LAUNCH_ADDITION_SLUGS,
    validate_seed_data,
)
from seed_entity_registry import MINIMUM_ENTITY_COUNT, _database_url  # noqa: E402


def test_launch_seed_is_unique_valid_and_above_minimum() -> None:
    validate_seed_data()

    slugs = [entity.entity_slug for entity in ENTITY_SEEDS]
    assert len(ENTITY_SEEDS) == 81
    assert len(ENTITY_SEEDS) >= MINIMUM_ENTITY_COUNT
    assert len(slugs) == len(set(slugs))
    assert {entity.entity_type for entity in ENTITY_SEEDS} <= ENTITY_TYPES


def test_authorized_nigeria_additions_are_present_and_nigeria_primary() -> None:
    additions = {
        entity.entity_slug: entity
        for entity in ENTITY_SEEDS
        if entity.entity_slug in NIGERIA_LAUNCH_ADDITION_SLUGS
    }

    assert len(NIGERIA_LAUNCH_ADDITION_SLUGS) == 14
    assert set(additions) == NIGERIA_LAUNCH_ADDITION_SLUGS
    assert all(entity.region == "NG" for entity in additions.values())
    assert all(entity.country_code == "NG" for entity in additions.values())


def test_spec_aliases_and_corrected_canonical_records_are_searchable() -> None:
    lookup_strings = {
        value.casefold()
        for entity in ENTITY_SEEDS
        for value in (entity.canonical_name, *entity.aliases)
    }

    assert {
        "teamapt",
        "sendwave",
        "wave",
        "national data protection commission",
        "national communications commission",
        "ndpc act 2023",
        "investment and securities act",
    } <= lookup_strings

    by_slug = {entity.entity_slug: entity for entity in ENTITY_SEEDS}
    assert by_slug["wave-mobile-money"].entity_slug != by_slug["sendwave"].entity_slug
    assert by_slug["quickteller"].parent_slug == "interswitch"
    assert by_slug["remita"].parent_slug == "systemspecs"
    assert by_slug["investments-and-securities-act-2025"].canonical_name.endswith(
        "2025"
    )


def test_database_url_accepts_sqlalchemy_async_scheme(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_WRITE", raising=False)

    assert _database_url("postgresql+asyncpg://user:pass@db/app") == (
        "postgresql://user:pass@db/app"
    )

