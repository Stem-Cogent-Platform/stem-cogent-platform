from uuid import uuid4

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
