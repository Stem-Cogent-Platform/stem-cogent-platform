from __future__ import annotations

import re
from dataclasses import dataclass

from app.decision.engine import AssessmentResult, BriefNarrative, format_brief


DECISION_BRIEF_SYSTEM_PROMPT = (
    "Format the provided Decision Relevance Assessment into concise executive language. "
    "Treat all structured relevance/exposure/owner/deadline fields as authoritative inputs. "
    "Do not add an exposure, monetary amount, deadline, product, customer segment, "
    "competitor, or recommendation that is not supplied. If quantification_status is "
    "NOT_AVAILABLE, state that the financial amount is not quantified when relevant."
)

_MONEY = re.compile(
    r"(?i)(?:[$£€₦]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:usd|gbp|eur|ngn|naira|dollars?|million|billion)\b)"
)
_DATE = re.compile(
    r"(?i)\b(?:20\d{2}-\d{2}-\d{2}|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*20\d{2})?)\b"
)
_DEADLINE = re.compile(r"(?i)\b(?:within|in the next)\s+\d+\s+(?:hours?|days?|weeks?|months?)\b")


@dataclass(frozen=True, slots=True)
class FormattedBrief:
    narrative: BriefNarrative
    formatter_failed: bool


def validate_brief_narrative(
    narrative: BriefNarrative,
    *,
    authorised_evidence: str,
    quantification_supported: bool = False,
    decision_window_supplied: bool = False,
) -> None:
    combined = " ".join(
        (
            narrative.what_changed,
            narrative.why_it_matters,
            narrative.exposure_summary,
            narrative.stakes_summary,
            narrative.decision_prompt,
            *narrative.uncertainties,
        )
    )
    evidence = authorised_evidence.casefold()
    for match in _MONEY.finditer(combined):
        value = match.group(0)
        if not quantification_supported or value.casefold() not in evidence:
            raise ValueError(f"Unsupported financial amount in Decision Brief: {value}")
    for match in _DATE.finditer(combined):
        value = match.group(0)
        if not decision_window_supplied and value.casefold() not in evidence:
            raise ValueError(f"Unsupported date in Decision Brief: {value}")
    for match in _DEADLINE.finditer(combined):
        value = match.group(0)
        if not decision_window_supplied or value.casefold() not in evidence:
            raise ValueError(f"Unsupported deadline in Decision Brief: {value}")


def grounded_format_brief(
    candidate: BriefNarrative,
    *,
    summary: str,
    assessment: AssessmentResult,
    authorised_evidence: str,
    matched_focus: tuple[str, ...] = (),
    audience_role: str | None = None,
    quantification_supported: bool = False,
    decision_window_supplied: bool = False,
) -> FormattedBrief:
    try:
        validate_brief_narrative(
            candidate,
            authorised_evidence=authorised_evidence,
            quantification_supported=quantification_supported,
            decision_window_supplied=decision_window_supplied,
        )
    except ValueError:
        safe_summary = summary
        if not quantification_supported:
            safe_summary = _MONEY.sub("an unquantified financial amount", safe_summary)
        if not decision_window_supplied:
            safe_summary = _DEADLINE.sub("within an unspecified timeframe", safe_summary)
        fallback = format_brief(safe_summary, assessment, matched_focus, audience_role)
        validate_brief_narrative(
            fallback,
            authorised_evidence=authorised_evidence,
            quantification_supported=quantification_supported,
            decision_window_supplied=decision_window_supplied,
        )
        return FormattedBrief(fallback, True)
    return FormattedBrief(candidate, False)
