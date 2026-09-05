from __future__ import annotations

from uuid import UUID

import pytest

from app.intelligence.synthesis import EvidenceItem, GlobalContextPackage
from app.intelligence.synthesis.service import (
    GLOBAL_INTELLIGENCE_SYSTEM_PROMPT,
    Citation,
    GlobalSynthesis,
    SynthesisService,
    SynthesisValidationError,
    validate_synthesis,
)


SIGNAL_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_prompt_defines_complete_claim_index_citation_contract() -> None:
    assert "summary is claim 0" in GLOBAL_INTELLIGENCE_SYSTEM_PROMPT
    assert "citation for every claim_index" in GLOBAL_INTELLIGENCE_SYSTEM_PROMPT
    assert "Copy each source_signal_id and source_name exactly" in (
        GLOBAL_INTELLIGENCE_SYSTEM_PROMPT
    )


def _context() -> GlobalContextPackage:
    return GlobalContextPackage(
        canonical_signal_id=SIGNAL_ID,
        primary_domain="REGULATORY_POLICY",
        event_type="CIRCULAR_ISSUED",
        entities=("Central Bank of Nigeria",),
        confidence_score="0.900",
        confidence_band="HIGH_CONFIDENCE",
        urgency_score="0.720",
        urgency_band="HIGH",
        evidence=(
            EvidenceItem(
                signal_id=SIGNAL_ID,
                source_name="Central Bank of Nigeria",
                title="Payment circular issued",
                body_text="On 2026-08-19, the CBN issued a payment circular.",
                source_url="https://www.cbn.gov.ng/circular",
                published_at="2026-08-19T09:00:00+00:00",
            ),
        ),
        historical_signal_ids=(),
        cluster_status=None,
        cluster_signal_count=None,
    )


def _valid_output() -> GlobalSynthesis:
    claims = [
        "The CBN issued a payment circular on 2026-08-19.",
        "A payment circular was issued.",
        "The circular is a regulatory development.",
        "The source-grounded confidence is high.",
    ]
    return GlobalSynthesis(
        summary=claims[0],
        key_developments=[claims[1]],
        global_implication=claims[2],
        confidence_note=claims[3],
        citations=[
            Citation(
                claim_index=index,
                source_signal_id=SIGNAL_ID,
                source_name="Central Bank of Nigeria",
            )
            for index in range(4)
        ],
    )


def test_valid_synthesis_requires_unbroken_evidence_citations() -> None:
    validate_synthesis(_valid_output(), _context())


@pytest.mark.parametrize(
    "unsupported",
    ["The impact is NGN 500 million.", "The deadline is 2026-09-30.", "Usage rose 45%."],
)
def test_validator_rejects_ungrounded_money_dates_and_statistics(unsupported: str) -> None:
    output = _valid_output().model_copy(update={"summary": unsupported})

    with pytest.raises(SynthesisValidationError, match="unsupported value"):
        validate_synthesis(output, _context())


def test_validator_rejects_detached_and_incomplete_citations() -> None:
    output = _valid_output().model_copy(
        update={
            "citations": [
                Citation(
                    claim_index=0,
                    source_signal_id=UUID("00000000-0000-0000-0000-000000000099"),
                    source_name="Unknown",
                )
            ]
        }
    )

    with pytest.raises(SynthesisValidationError):
        validate_synthesis(output, _context())


class _HallucinatingClient:
    async def generate(self, **kwargs):  # type: ignore[no-untyped-def]
        return {
            "summary": "The impact is USD 9 billion on 2026-12-31.",
            "key_developments": ["Unsupported development"],
            "global_implication": "Unsupported implication",
            "confidence_note": "Unsupported confidence",
            "citations": [
                {
                    "claim_index": index,
                    "source_signal_id": str(SIGNAL_ID),
                    "source_name": "Central Bank of Nigeria",
                }
                for index in range(4)
            ],
        }


@pytest.mark.asyncio
async def test_adversarial_generation_triggers_grounded_fallback() -> None:
    output, failed = await SynthesisService(_HallucinatingClient()).synthesize(  # type: ignore[arg-type]
        _context()
    )

    assert failed is True
    assert "USD 9 billion" not in output.summary
    assert "2026-12-31" not in output.summary
    assert {citation.source_signal_id for citation in output.citations} == {SIGNAL_ID}
