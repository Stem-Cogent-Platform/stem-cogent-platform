from uuid import uuid4

import pytest

from app.intelligence.decision_paths import generate_decision_paths


@pytest.mark.parametrize(
    "decision_type,expected",
    (
        ("REGULATORY_IMPLEMENTATION", {"MONITOR", "ESCALATE", "COMMUNICATE"}),
        ("REROUTE_OR_FAILOVER", {"MONITOR", "REROUTE", "ESCALATE", "COMMUNICATE"}),
        ("PRICING_RESPONSE", {"MONITOR", "ESCALATE", "COMMUNICATE"}),
    ),
)
def test_launch_decision_paths_are_bounded(decision_type: str, expected: set[str]) -> None:
    evidence_id = uuid4()
    guidance = generate_decision_paths(
        decision_type, ("Configured context",), (evidence_id,), ("REMAINS_UNKNOWN",)
    )

    assert guidance.status == "READY"
    assert {option.option_code for option in guidance.response_options} == expected
    assert all(option.evidence_signal_ids == (str(evidence_id),) for option in guidance.response_options)
    assert "best" not in " ".join(option.description for option in guidance.response_options).casefold()


def test_insufficient_context_returns_validation_not_speculation() -> None:
    guidance = generate_decision_paths("REROUTE_OR_FAILOVER", (), (uuid4(),), ())

    assert guidance.status == "INSUFFICIENT_CONTEXT"
    assert guidance.next_validation_steps
