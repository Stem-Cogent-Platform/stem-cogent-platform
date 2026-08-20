from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_BATCH_SIZE = 5
_TAXONOMY_TERM_COUNT = 3
_ROTATION_SECONDS = 600


def _quoted(value: str) -> str:
    cleaned = " ".join(value.replace('"', " ").split())
    return f'"{cleaned}"'


def build_gdelt_url(
    base_url: str,
    entity_names: tuple[str, ...],
    taxonomy_terms: tuple[str, ...],
) -> str:
    terms = tuple(dict.fromkeys((*entity_names, *taxonomy_terms)))
    if not terms:
        raise RuntimeError("Discovery requires an entity or taxonomy term")
    query = f"({' OR '.join(_quoted(term) for term in terms)}) (Nigeria OR Nigerian)"
    return f"{base_url}?{urlencode({'query': query, 'mode': 'artlist', 'maxrecords': 75, 'format': 'json', 'sort': 'hybridrel', 'timespan': '1day'})}"


async def build_rotating_discovery_url(
    session: AsyncSession,
    base_url: str,
    scheduled_at: datetime,
) -> str:
    entity_rows = (
        await session.execute(
            text(
                """
                SELECT canonical_name, aliases
                FROM intelligence.entities
                WHERE active
                  AND metadata -> 'launch_roles' ? 'PRIORITY_FINTECH'
                ORDER BY canonical_name, id
                """
            )
        )
    ).mappings().all()
    taxonomy_rows = (
        await session.execute(
            text(
                """
                SELECT DISTINCT subcategory_code
                FROM config.signal_taxonomy
                WHERE active
                ORDER BY subcategory_code
                """
            )
        )
    ).scalars().all()
    if not entity_rows and not taxonomy_rows:
        raise RuntimeError("Discovery registry and taxonomy are empty")

    rotation = int(scheduled_at.timestamp()) // _ROTATION_SECONDS
    selected_entities = _rotating_slice(tuple(entity_rows), rotation, _BATCH_SIZE)
    entities = tuple(
        term
        for row in selected_entities
        for term in _entity_terms(row["canonical_name"], tuple(row["aliases"]))
    )
    taxonomy = tuple(
        value.replace("_", " ").lower()
        for value in _rotating_slice(
            tuple(taxonomy_rows),
            rotation * _TAXONOMY_TERM_COUNT,
            _TAXONOMY_TERM_COUNT,
        )
    )
    return build_gdelt_url(base_url, entities, taxonomy)


def _entity_terms(canonical_name: str, aliases: tuple[str, ...]) -> tuple[str, ...]:
    distinct_aliases = tuple(
        alias
        for alias in aliases
        if alias.casefold() != canonical_name.casefold() and len(alias) >= 3
    )
    return (canonical_name, *distinct_aliases[:1])


def _rotating_slice(values: tuple, offset: int, size: int) -> tuple:
    if not values:
        return ()
    return tuple(values[(offset + index) % len(values)] for index in range(min(size, len(values))))
