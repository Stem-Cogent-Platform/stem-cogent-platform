"""Synthesis module — 3 core intelligence artifact engines.

Provides strict Pydantic data contracts and the ArtifactSynthesizer service for
generating structured intelligence artifacts from promoted signals:

1. ComplianceGapPayload — regulatory_mandate → compliance_gap
2. CompetitorStrategicPayload — competitor_move → competitive_battlecard
3. RailDegradationPayload — rail_degradation → rail_stress
"""

from app.synthesis.context import ArtifactContextPackage
from app.synthesis.models import (
    ARTIFACT_TYPE_MAP,
    ELIGIBLE_SIGNAL_TYPES,
    ActionItem,
    BusinessFunction,
    CompetitiveBattlecardPayload,
    CompetitorStrategicPayload,
    ComplianceGapMatrixPayload,
    ComplianceGapPayload,
    Confidence,
    IntelligenceArtifactListResponse,
    IntelligenceArtifactResponse,
    MultiDimensionalImpact,
    RailDegradationPayload,
    RailStressPayload,
    Severity,
    StrategicOption,
    Urgency,
)
from app.synthesis.synthesizer import (
    ArtifactSynthesisError,
    ArtifactSynthesisResult,
    ArtifactSynthesizer,
)

__all__ = [
    "ARTIFACT_TYPE_MAP",
    "ActionItem",
    "ArtifactContextPackage",
    "ArtifactSynthesisError",
    "ArtifactSynthesisResult",
    "ArtifactSynthesizer",
    "BusinessFunction",
    "CompetitiveBattlecardPayload",
    "CompetitorStrategicPayload",
    "ComplianceGapMatrixPayload",
    "ComplianceGapPayload",
    "Confidence",
    "ELIGIBLE_SIGNAL_TYPES",
    "IntelligenceArtifactListResponse",
    "IntelligenceArtifactResponse",
    "MultiDimensionalImpact",
    "RailDegradationPayload",
    "RailStressPayload",
    "Severity",
    "StrategicOption",
    "Urgency",
]
