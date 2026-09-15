from uuid import uuid4

import pytest

from app.context.entity_resolution import RegistryEntity, resolve_context_value


def test_known_context_aliases_resolve_deterministically() -> None:
    nibss_id = uuid4()
    registry = (
        RegistryEntity(
            nibss_id,
            "Nigeria Inter-Bank Settlement System",
            ("NIBSS", "NIBSS Plc"),
        ),
    )

    result = resolve_context_value("DEPENDENCY", "nibss", registry)

    assert result.status == "RESOLVED"
    assert result.entity_id == nibss_id
    assert result.method == "ALIAS_EXACT"


def test_ambiguous_and_free_text_context_are_not_silently_linked() -> None:
    registry = (
        RegistryEntity(uuid4(), "Anchor API", ("Anchor",)),
        RegistryEntity(uuid4(), "Anchor Bank", ("Anchor",)),
    )

    ambiguous = resolve_context_value("COMPETITOR", "Anchor", registry)
    priority = resolve_context_value("INITIATIVE", "Improve merchant profitability", registry)

    assert ambiguous.status == "AMBIGUOUS"
    assert ambiguous.entity_id is None
    assert priority.status == "NOT_APPLICABLE"


@pytest.mark.parametrize("description,alias", [
    ("CBN Operational License", "CBN"),
    ("NIBSS Instant Payments Integration", "NIBSS"),
    ("Providus Bank settlement services", "Providus Bank"),
])
def test_descriptive_dependencies_resolve_known_provider(description, alias):
    entity = RegistryEntity(uuid4(), alias, (alias,))
    result = resolve_context_value("DEPENDENCY", description, (entity,))
    assert result.entity_id == entity.id
    assert result.method == "DESCRIPTIVE_REFERENCE"


@pytest.mark.parametrize("description", [
    "Commercial Settlement Banks", "PCI-DSS Compliance Certificate",
    "Not CBN licensed", "CBN or NIBSS integration", "Access banking services",
    "CBNish payment integration",
])
def test_generic_or_uncertain_descriptions_do_not_invent_entities(description):
    registry = (RegistryEntity(uuid4(), "Central Bank of Nigeria", ("CBN",)),
                RegistryEntity(uuid4(), "Nigeria Inter-Bank Settlement System", ("NIBSS",)),
                RegistryEntity(uuid4(), "Access Bank", ("Access",)))
    result = resolve_context_value("DEPENDENCY", description, registry)
    assert result.entity_id is None


def test_descriptive_alias_collision_requires_review():
    registry = (RegistryEntity(uuid4(), "First provider", ("NIP",)),
                RegistryEntity(uuid4(), "Second provider", ("NIP",)))
    result = resolve_context_value("DEPENDENCY", "NIP payments integration", registry)
    assert result.status == "AMBIGUOUS"
    assert result.entity_id is None
