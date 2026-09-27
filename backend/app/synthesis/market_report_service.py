"""Market Report Generator & Vertical Intelligence Service.

Synthesizes CB Insights-style market intelligence reports tailored for Nigerian
and African fintech verticals without introducing redundant services.
Leverages pipeline.signals, pipeline.competitor_dossiers, and search_live_intelligence.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.web_search import search_live_intelligence
from app.intelligence.synthesis.router import build_generation_client
from app.synthesis.market_models import MarketReportPayload

logger = logging.getLogger(__name__)

SECTOR_CATALOG: dict[str, dict[str, Any]] = {
    "cross-border-fx": {
        "title": "B2B Cross-Border & FX Settlement",
        "description": "Cross-border payment corridors, IMTO remittance rails, FX spreads, and international trade settlement.",
        "jurisdiction": "Nigeria",
        "primary_regulators": ["CBN", "SEC", "NFIU"],
        "signal_tags": [
            "Cross-Border FX",
            "B2B Settlements",
            "Cross-Border Payments",
            "Cross-Border Settlement",
            "Remittances",
            "International Payments",
            "cross-border-fx",
        ],
        "dossier_segments": [
            "Cross-Border FX",
            "International Payments",
            "Trade Settlement",
            "Remittances",
            "Cross-border / Payments",
        ],
        "search_query": "Nigeria B2B cross-border FX payments settlement IMTO Providus CBN circulars 2025 2026",
    },
    "virtual-accounts": {
        "title": "Virtual Account Issuance & Collections",
        "description": "Dynamic virtual account generation, merchant checkout acquiring, BaaS partner banks, and collection webhooks.",
        "jurisdiction": "Nigeria",
        "primary_regulators": ["CBN", "NIBSS"],
        "signal_tags": [
            "Virtual Accounts",
            "Collections",
            "Direct Debit",
            "Payment Gateway",
            "Merchant Acquiring",
            "Payment Processing",
            "virtual-accounts",
        ],
        "dossier_segments": [
            "Virtual Accounts",
            "Collections",
            "Merchant Acquiring",
            "Payments / Wallets / Processing",
        ],
        "search_query": "Nigeria virtual accounts issuance collections Wema ALAT Providus NIBSS NIP fees 2025 2026",
    },
    "agency-banking": {
        "title": "POS Agency Banking & Cash-In/Cash-Out",
        "description": "Last-mile cash distribution, POS terminal acquiring networks, SANEF agent compliance, and interchange economics.",
        "jurisdiction": "Nigeria",
        "primary_regulators": ["CBN", "SANEF", "NIBSS"],
        "signal_tags": [
            "Agent Banking",
            "Agency Banking",
            "POS Merchant Acquiring",
            "CICO",
            "Super Agent",
            "agency-banking",
        ],
        "dossier_segments": [
            "Agent Banking",
            "Agency Banking",
            "POS Merchant Acquiring",
            "Super Agent",
        ],
        "search_query": "Nigeria POS agency banking cash-in cash-out Moniepoint OPay PalmPay CBN interchange cap 2025 2026",
    },
    "digital-lending": {
        "title": "Digital Lending & Credit Infrastructure",
        "description": "Consumer and SME digital lending, credit scoring APIs, FCCPC lending regulations, and default recovery rails.",
        "jurisdiction": "Nigeria",
        "primary_regulators": ["CBN", "FCCPC", "NDPC"],
        "signal_tags": [
            "Digital Lending",
            "Lending",
            "SME Lending",
            "Buy Now Pay Later",
            "Credit Infrastructure",
            "digital-lending",
        ],
        "dossier_segments": [
            "Digital Lending",
            "Lending / Credit",
            "SME Lending",
            "Credit Infrastructure",
        ],
        "search_query": "Nigeria digital lending FCCPC approval credit infrastructure interest rate caps default recovery 2025 2026",
    },
}

MARKET_REPORT_PROMPT = """You are a Principal Financial Systems Architect and CB Insights-style market intelligence research director specializing in African fintech and banking infrastructure.
Synthesize an authoritative, highly factual Market Intelligence Report strictly adhering to the JSON schema.

System Directives:
1. Market Map & Players:
   - Categorize identified operating entities into 'Leader', 'Challenger', or 'Niche Specialist'.
   - Detail their core product offering, licensing moat (e.g., 'National MFB', 'PSSP via Providus', 'IMTO License', 'Switching & Processing License'), and known underlying partner banks or clearing switches (e.g., 'Providus Bank Core', 'Wema ALAT', 'NIBSS Instant Payment (NIP)', 'Interswitch Core Switch', 'Zenith Bank Direct').
2. Commercial Economics:
   - Provide concrete fee benchmarks, interchange caps, spread compression, and take-rate dynamics relevant to this vertical in Nigeria.
3. Regulatory Headwinds:
   - List active CBN/SEC/FCCPC circulars, enforcement trends, statutory compliance requirements, and operational scrutiny points.
4. Strategic Outlook:
   - Deliver an actionable 6 to 12-month forward-looking assessment of market infrastructure shifts, margin pressure, partner bank concentration, and consolidation.

Base your synthesis objectively on the provided historical signals, competitor dossiers, and live web intelligence. Do not include ungrounded speculation.
"""


def get_sector_metadata(sector_slug: str) -> dict[str, Any]:
    if sector_slug in SECTOR_CATALOG:
        return SECTOR_CATALOG[sector_slug]
    clean_title = sector_slug.replace("-", " ").replace("_", " ").title()
    return {
        "title": clean_title,
        "description": f"Vertical intelligence report for {clean_title}.",
        "jurisdiction": "Nigeria",
        "primary_regulators": ["CBN"],
        "signal_tags": [clean_title, sector_slug],
        "dossier_segments": [clean_title],
        "search_query": f"Nigeria {clean_title} fintech licensing rails market 2025 2026",
    }


async def fetch_sector_signals(
    session: AsyncSession,
    sector_slug: str,
    limit: int = 15,
) -> list[dict[str, Any]]:
    meta = get_sector_metadata(sector_slug)
    tags = meta["signal_tags"]
    search_term = sector_slug.replace("-", " ")

    query = text(
        """
        SELECT id, signal_type, urgency, sentiment, primary_entity, secondary_entities,
               affected_sectors, executive_summary, title, body_text,
               statutory_deadline, financial_impact_indicator, created_at
        FROM pipeline.signals
        WHERE (
            affected_sectors && :tags
            OR strpos(lower(coalesce(title, '') || ' ' || coalesce(body_text, '')), :search_term) > 0
        )
        AND (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )
    result = await session.execute(query, {"tags": tags, "search_term": search_term.lower(), "limit": limit})
    rows = result.mappings().all()
    return [
        {
            "id": str(r["id"]),
            "signal_type": r["signal_type"],
            "urgency": r["urgency"],
            "sentiment": r["sentiment"],
            "primary_entity": r["primary_entity"],
            "secondary_entities": r["secondary_entities"],
            "affected_sectors": r["affected_sectors"],
            "executive_summary": r["executive_summary"],
            "title": r["title"],
            "body_excerpt": (r["body_text"] or "")[:1500],
            "statutory_deadline": str(r["statutory_deadline"]) if r["statutory_deadline"] else None,
            "financial_impact_indicator": r["financial_impact_indicator"],
        }
        for r in rows
    ]


async def fetch_sector_dossiers(
    session: AsyncSession,
    sector_slug: str,
    limit: int = 15,
) -> list[dict[str, Any]]:
    meta = get_sector_metadata(sector_slug)
    segments = meta["dossier_segments"]
    search_term = sector_slug.replace("-", " ")

    query = text(
        """
        SELECT DISTINCT ON (competitor_name)
            id, competitor_name, canonical_domain, known_licenses,
            primary_settlement_rails, fee_model_summary, core_target_segments, profile
        FROM pipeline.competitor_dossiers
        WHERE (
            core_target_segments && :segments
            OR strpos(lower(competitor_name || ' ' || coalesce(fee_model_summary, '')), :search_term) > 0
        )
        AND processing_status = 'ready'
        AND organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        ORDER BY competitor_name, last_refreshed_at DESC NULLS LAST
        LIMIT :limit
        """
    )
    result = await session.execute(query, {"segments": segments, "search_term": search_term.lower(), "limit": limit})
    rows = result.mappings().all()
    return [
        {
            "competitor_name": r["competitor_name"],
            "canonical_domain": r["canonical_domain"],
            "known_licenses": r["known_licenses"],
            "primary_settlement_rails": r["primary_settlement_rails"],
            "fee_model_summary": r["fee_model_summary"],
            "core_target_segments": r["core_target_segments"],
        }
        for r in rows
    ]


async def synthesize_market_report(
    session: AsyncSession,
    sector_slug: str,
    *,
    client: Any | None = None,
    search_fn: Callable[..., Any] | None = None,
) -> MarketReportPayload:
    meta = get_sector_metadata(sector_slug)
    sector_title = meta["title"]
    jurisdiction = meta["jurisdiction"]

    # 1. Gather historical signals from pipeline.signals
    signals = await fetch_sector_signals(session, sector_slug)

    # 2. Gather verified competitor profiles & rail footprints
    dossiers = await fetch_sector_dossiers(session, sector_slug)

    # 3. Live search landscape verification via search_live_intelligence
    search_runner = search_fn or search_live_intelligence
    web_results: list[dict[str, Any]] = []
    try:
        search_res = await search_runner(
            query=meta["search_query"],
            geo_scope="regional",
            num_results=6,
        )
        web_results = search_res.get("results", [])
    except Exception as exc:
        logger.warning(
            "Live intelligence search encountered an error; continuing with database sources",
            extra={"error": str(exc), "sector_slug": sector_slug},
        )

    if not signals and not dossiers and not web_results:
        raise ValueError("No source evidence is available for this market report")

    # 4. Invoke Structured LLM Generation Client
    owned_client = client is None
    gen_client = client or build_generation_client()

    context_data = {
        "sector_slug": sector_slug,
        "sector_title": sector_title,
        "jurisdiction": jurisdiction,
        "historical_signals": signals,
        "known_competitor_dossiers": dossiers,
        "live_web_intelligence": [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": (item.get("text") or "")[:2000],
            }
            for item in web_results
        ],
    }

    try:
        raw_response = await gen_client.generate(
            instructions=MARKET_REPORT_PROMPT,
            context=context_data,
            schema=MarketReportPayload.model_json_schema(),
            max_output_tokens=6500,
        )
        # 5. Strict Pydantic validation (extra keys forbidden)
        report_payload = MarketReportPayload.model_validate(raw_response)
        return report_payload
    finally:
        if owned_client:
            await gen_client.aclose()


async def save_market_report(
    session: AsyncSession,
    sector_slug: str,
    report: MarketReportPayload,
    primary_jurisdiction: str = "Nigeria",
) -> dict[str, Any]:
    meta = get_sector_metadata(sector_slug)
    sector_title = meta["title"]
    entities_count = len(report.players)
    payload_json = report.model_dump_json()

    query = text(
        """
        INSERT INTO pipeline.market_reports (
            tenant_id, sector_slug, sector_title, primary_jurisdiction, report_payload,
            monitored_entities_count, last_generated_at
        ) VALUES (
            NULLIF(current_setting('app.current_tenant_id', true), '')::uuid,
            :sector_slug, :sector_title, :primary_jurisdiction, CAST(:report_payload AS JSONB),
            :monitored_entities_count, clock_timestamp()
        )
        ON CONFLICT (tenant_id, sector_slug) DO UPDATE SET
            sector_title = EXCLUDED.sector_title,
            primary_jurisdiction = EXCLUDED.primary_jurisdiction,
            report_payload = EXCLUDED.report_payload,
            monitored_entities_count = EXCLUDED.monitored_entities_count,
            last_generated_at = EXCLUDED.last_generated_at
        RETURNING id, sector_slug, sector_title, primary_jurisdiction, report_payload,
                  monitored_entities_count, last_generated_at, created_at;
        """
    )
    result = await session.execute(
        query,
        {
            "sector_slug": sector_slug,
            "sector_title": sector_title,
            "primary_jurisdiction": primary_jurisdiction,
            "report_payload": payload_json,
            "monitored_entities_count": entities_count,
        },
    )
    row = result.mappings().one()
    return dict(row)


async def get_market_report_by_slug(
    session: AsyncSession,
    sector_slug: str,
) -> dict[str, Any] | None:
    query = text(
        """
        SELECT id, sector_slug, sector_title, primary_jurisdiction, report_payload,
               monitored_entities_count, last_generated_at, created_at
        FROM pipeline.market_reports
        WHERE sector_slug = :sector_slug
          AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        """
    )
    result = await session.execute(query, {"sector_slug": sector_slug})
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def list_market_reports(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT id, sector_slug, sector_title, primary_jurisdiction, report_payload,
               monitored_entities_count, last_generated_at, created_at
        FROM pipeline.market_reports
        WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        ORDER BY sector_slug ASC
        """
    )
    result = await session.execute(query)
    rows = result.mappings().all()
    existing_by_slug = {r["sector_slug"]: dict(r) for r in rows}

    catalog_entries: list[dict[str, Any]] = []
    for slug, meta in SECTOR_CATALOG.items():
        if slug in existing_by_slug:
            catalog_entries.append(existing_by_slug[slug])
        else:
            catalog_entries.append(
                {
                    "id": None,
                    "sector_slug": slug,
                    "sector_title": meta["title"],
                    "primary_jurisdiction": meta["jurisdiction"],
                    "report_payload": None,
                    "monitored_entities_count": 0,
                    "last_generated_at": None,
                    "created_at": None,
                    "description": meta["description"],
                }
            )

    for slug, entry in existing_by_slug.items():
        if slug not in SECTOR_CATALOG:
            catalog_entries.append(entry)

    return catalog_entries
