from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

SourceKind = Literal[
    "user_input",
    "documented",
    "measured",
    "derived",
    "literature",
    "calibrated",
]
EstimateKind = Literal[
    "direct",
    "derived",
    "indicator",
    "calibrated_prediction",
]
Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Interval:
    """Closed numeric interval used for explicit engineering uncertainty."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = float(self.lower)
        upper = float(self.upper)
        if not math.isfinite(lower) or not math.isfinite(upper):
            raise ValueError("engineering interval bounds must be finite")
        if lower > upper:
            raise ValueError("engineering interval lower bound must be <= upper bound")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class SourceRef:
    """Traceable origin for an engineering input or model parameter."""

    source_kind: SourceKind
    reference: str
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in {
            "user_input",
            "documented",
            "measured",
            "derived",
            "literature",
            "calibrated",
        }:
            raise ValueError(f"unsupported engineering source kind: {self.source_kind!r}")
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise ValueError("engineering source reference must be a non-empty string")
        object.__setattr__(self, "reference", self.reference.strip())
        if self.detail is not None:
            if not isinstance(self.detail, str) or not self.detail.strip():
                raise ValueError("engineering source detail must be a non-empty string when provided")
            object.__setattr__(self, "detail", self.detail.strip())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EngineeringResult:
    """A scalar engineering result with explicit meaning and traceability.

    Low-level deterministic equations may return plain floats. This wrapper is
    intended for user-facing composed results where provenance, confidence,
    assumptions or uncertainty must remain attached to the numeric value.
    """

    value: float | None
    unit: str
    estimate_kind: EstimateKind
    confidence: Confidence
    uncertainty: Interval | None = None
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        if self.value is not None:
            value = float(self.value)
            if not math.isfinite(value):
                raise ValueError("engineering result value must be finite when available")
            object.__setattr__(self, "value", value)
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("engineering result unit must be a non-empty string")
        object.__setattr__(self, "unit", self.unit.strip())
        if self.estimate_kind not in {"direct", "derived", "indicator", "calibrated_prediction"}:
            raise ValueError(f"unsupported engineering estimate kind: {self.estimate_kind!r}")
        if self.confidence not in {"high", "medium", "low"}:
            raise ValueError(f"unsupported engineering confidence: {self.confidence!r}")
        object.__setattr__(self, "assumptions", tuple(str(item) for item in self.assumptions))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "provenance", tuple(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
