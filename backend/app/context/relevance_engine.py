"""Company Context Relevance Engine — Two-Tier Matcher.

Tier 1: Deterministic fast filter using set intersection of signal fields
against tenant operational footprint (operating_licenses, active_products,
clearing_rails).

Tier 2: Role-specific action bifurcation via structured LLM synthesis
generating concrete, differentiated action points for Product, CFO, and
Compliance lenses.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.context.relevance_models import (
    ExposureResult,
    LensAction,
    LensImpact,
    LensSynthesisPayload,
)
from app.core.config import get_settings
from app.core.secrets import get_scalar_secret

logger = logging.getLogger(__name__)

LENS_SYNTHESIS_SYSTEM_PROMPT = """\
You are a senior fintech operational analyst producing role-specific action items \
for a company affected by a market/regulatory/infrastructure signal.

Given the signal context and the company's matched operational exposure, produce \
THREE completely distinct, non-overlapping action payloads for:

1. PRODUCT LENS (Product/Engineering): UX/API changes, fallback rail configuration, \
customer notification needs, feature roadmap implications.
2. CFO LENS (Finance): Liquidity float exposure, transaction fee margin risks, \
regulatory fines, revenue impact quantification.
3. COMPLIANCE LENS (Legal/Regulatory): Reporting obligations, circular audit \
checklists, statutory deadlines, license compliance actions.

Rules:
- STRICTLY OBJECTIVE, ACTIONABLE language. Zero essays, zero generic advice.
- Each lens MUST address a DIFFERENT operational concern. No overlap.
- Impact: What specifically happened that affects this role.
- Action item: One concrete next step this role must take.
- Urgency: immediate (active outage/enforcement), within_24h (near-term deadline), \
within_week (planning required), monitor (awareness only).
"""


def _normalise(value: str) -> str:
    """Lowercase and strip a value for comparison."""
    return value.strip().lower()


def _normalise_set(values: list[str] | tuple[str, ...]) -> set[str]:
    """Create a normalised set from a list of values."""
    return {_normalise(v) for v in values if v and v.strip()}


def compute_exposure(
    signal_data: dict[str, Any],
    company_profile: dict[str, Any],
) -> ExposureResult:
    """Tier 1: Deterministic set intersection of signal fields against tenant profile.

    Parameters
    ----------
    signal_data : dict
        Must contain: affected_sectors (list[str]), primary_entity (str),
        secondary_entities (list[str]), urgency (str).
    company_profile : dict
        Must contain: operating_licenses (list[str]), active_products (list[str]),
        clearing_rails (list[str]).

    Returns
    -------
    ExposureResult with exposure_tier and matched_nodes.
    """
    # Build normalised signal surfaces
    signal_sectors = _normalise_set(signal_data.get("affected_sectors", []))
    signal_primary = _normalise(signal_data.get("primary_entity", ""))
    signal_secondary = _normalise_set(signal_data.get("secondary_entities", []))
    signal_all_entities = signal_secondary | ({signal_primary} if signal_primary else set())
    signal_surface = signal_sectors | signal_all_entities

    # Build normalised tenant surfaces
    tenant_licenses = _normalise_set(company_profile.get("operating_licenses", []))
    tenant_products = _normalise_set(company_profile.get("active_products", []))
    tenant_rails = _normalise_set(company_profile.get("clearing_rails", []))

    # Intersect
    matched_rails = signal_surface & tenant_rails
    matched_licenses = signal_surface & tenant_licenses
    matched_products = signal_surface & tenant_products

    matched_nodes: dict[str, list[str]] = {}
    if matched_rails:
        matched_nodes["matched_rails"] = sorted(matched_rails)
    if matched_licenses:
        matched_nodes["matched_licenses"] = sorted(matched_licenses)
    if matched_products:
        matched_nodes["matched_products"] = sorted(matched_products)

    has_any_match = bool(matched_nodes)

    if not has_any_match:
        return ExposureResult(exposure_tier="irrelevant", matched_nodes={})

    urgency = _normalise(signal_data.get("urgency", "low"))

    # Direct infrastructure or license match → critical_direct
    if matched_rails or matched_licenses:
        return ExposureResult(
            exposure_tier="critical_direct",
            matched_nodes=matched_nodes,
        )

    # Product match with high/critical urgency → critical_direct
    if matched_products and urgency in ("critical", "high"):
        return ExposureResult(
            exposure_tier="critical_direct",
            matched_nodes=matched_nodes,
        )

    # Product match with lower urgency → moderate_indirect
    if matched_products:
        return ExposureResult(
            exposure_tier="moderate_indirect",
            matched_nodes=matched_nodes,
        )

    # Shouldn't reach here given the guard above, but defensive
    return ExposureResult(
        exposure_tier="low_observation",
        matched_nodes=matched_nodes,
    )


async def synthesize_lens_impact(
    signal_data: dict[str, Any],
    matched_nodes: dict[str, list[str]],
    exposure_tier: str,
    *,
    http_client: Any | None = None,
) -> LensImpact:
    """Tier 2: Generate role-specific action payloads via structured LLM synthesis.

    Falls back to deterministic placeholders if LLM is unavailable.
    """
    settings = get_settings()

    # Prepare context for LLM
    user_context = {
        "signal_type": signal_data.get("signal_type", "unknown"),
        "urgency": signal_data.get("urgency", "low"),
        "sentiment": signal_data.get("sentiment", "neutral"),
        "primary_entity": signal_data.get("primary_entity", ""),
        "executive_summary": signal_data.get("executive_summary", ""),
        "affected_sectors": signal_data.get("affected_sectors", []),
        "secondary_entities": signal_data.get("secondary_entities", []),
        "statutory_deadline": signal_data.get("statutory_deadline"),
        "financial_impact_indicator": signal_data.get("financial_impact_indicator"),
        "exposure_tier": exposure_tier,
        "matched_nodes": matched_nodes,
    }

    # Build schema for structured output
    schema = LensSynthesisPayload.model_json_schema()
    schema["additionalProperties"] = False
    if "properties" in schema:
        schema["required"] = list(schema["properties"].keys())
    # Flatten $defs for strict mode compatibility
    schema = _flatten_schema_defs(schema)

    try:
        raw_result = await _call_llm(user_context, schema, settings, http_client)
        parsed = LensSynthesisPayload.model_validate(raw_result)
        return LensImpact(
            product_lens=parsed.product_lens,
            cfo_lens=parsed.cfo_lens,
            compliance_lens=parsed.compliance_lens,
        )
    except Exception as exc:
        logger.warning(
            "Lens synthesis LLM call failed, using deterministic fallback: %s",
            exc,
        )
        return _deterministic_fallback(signal_data, matched_nodes, exposure_tier)


def _flatten_schema_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline $defs references for OpenAI strict mode compatibility."""
    defs = schema.pop("$defs", {})
    if not defs:
        return schema

    def _resolve(obj: Any) -> Any:
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_name = obj["$ref"].rsplit("/", 1)[-1]
                if ref_name in defs:
                    resolved = dict(defs[ref_name])
                    resolved["additionalProperties"] = False
                    if "properties" in resolved:
                        resolved["required"] = list(resolved["properties"].keys())
                    return _resolve(resolved)
            return {k: _resolve(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_resolve(item) for item in obj]
        return obj

    return _resolve(schema)


async def _call_llm(
    context: dict[str, Any],
    schema: dict[str, Any],
    settings: Any,
    http_client: Any | None,
) -> dict[str, Any]:
    """Call the LLM provider for lens synthesis."""
    import httpx

    api_key: str | None = None
    provider = settings.LLM_PRIMARY_PROVIDER
    model = settings.LLM_PRIMARY_MODEL

    if provider == "openai" and settings.OPENAI_API_KEY_ARN:
        try:
            api_key = get_scalar_secret(settings.OPENAI_API_KEY_ARN)
        except Exception:
            pass

    if not api_key and settings.GROQ_API_KEY_ARN:
        provider = "groq"
        model = settings.LLM_FALLBACK_MODEL
        try:
            api_key = get_scalar_secret(settings.GROQ_API_KEY_ARN)
        except Exception:
            pass

    if not api_key:
        raise RuntimeError(f"No API key available for lens synthesis ({provider})")

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS)

    try:
        if provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            body: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": LENS_SYNTHESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context, sort_keys=True)},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "lens_synthesis",
                        "strict": True,
                        "schema": schema,
                    },
                },
                "temperature": 0.0,
            }
        else:
            url = "https://api.groq.com/openai/v1/chat/completions"
            body = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"{LENS_SYNTHESIS_SYSTEM_PROMPT}\n"
                            f"Return one JSON object strictly matching this schema: "
                            f"{json.dumps(schema, separators=(',', ':'), sort_keys=True)}"
                        ),
                    },
                    {"role": "user", "content": json.dumps(context, sort_keys=True)},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }

        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return json.loads(content)
        return content
    finally:
        if owns_client:
            await client.aclose()


def _deterministic_fallback(
    signal_data: dict[str, Any],
    matched_nodes: dict[str, list[str]],
    exposure_tier: str,
) -> LensImpact:
    """Generate conservative, deterministic action items when LLM is unavailable."""
    entity = signal_data.get("primary_entity", "Unknown entity")
    urgency = signal_data.get("urgency", "low")
    signal_type = signal_data.get("signal_type", "general_industry")

    urgency_map = {
        "critical": "immediate",
        "high": "within_24h",
        "moderate": "within_week",
        "low": "monitor",
    }
    lens_urgency = urgency_map.get(urgency, "monitor")

    matched_items = []
    for category, items in matched_nodes.items():
        matched_items.extend(items)
    matched_str = ", ".join(matched_items[:5]) or "unspecified dependencies"

    if signal_type == "rail_degradation":
        product_impact = f"Active service disruption by {entity} may affect transaction processing on {matched_str}."
        product_action = "Verify failover rail configuration and enable fallback routing for affected payment channels."
        cfo_impact = f"Settlement delays via {entity} may increase float exposure and pending transaction liability."
        cfo_action = f"Quantify unsettled transaction volume on {matched_str} and assess liquidity buffer adequacy."
        compliance_impact = f"Service disruption by {entity} may trigger mandatory incident reporting obligations."
        compliance_action = "Check regulatory incident notification thresholds and prepare disclosure if required."
    elif signal_type == "regulatory_mandate":
        product_impact = f"Regulatory action by {entity} may require product changes affecting {matched_str}."
        product_action = "Audit affected product flows against the new requirements and scope implementation changes."
        cfo_impact = f"Regulatory mandate by {entity} may introduce new fee structures or capital requirements."
        cfo_action = f"Model financial impact of compliance costs and assess margin implications on {matched_str}."
        compliance_impact = f"New regulatory directive from {entity} may impose compliance deadlines and reporting requirements."
        compliance_action = "Map directive requirements to current compliance posture and identify gaps."
    else:
        product_impact = f"Development involving {entity} may affect product operations on {matched_str}."
        product_action = "Assess whether product roadmap adjustments are needed based on the development."
        cfo_impact = f"Market development involving {entity} may have financial implications for {matched_str}."
        cfo_action = "Evaluate potential revenue or cost impact and update financial projections if material."
        compliance_impact = f"Development involving {entity} should be reviewed for compliance implications."
        compliance_action = "Monitor for regulatory follow-up actions and update compliance tracking as needed."

    return LensImpact(
        product_lens=LensAction(
            impact=product_impact,
            action_item=product_action,
            urgency=lens_urgency,
        ),
        cfo_lens=LensAction(
            impact=cfo_impact,
            action_item=cfo_action,
            urgency=lens_urgency,
        ),
        compliance_lens=LensAction(
            impact=compliance_impact,
            action_item=compliance_action,
            urgency=lens_urgency,
        ),
    )
