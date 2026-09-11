from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .._strict import require_number

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


def _validated_text_items(items: object, field: str) -> tuple[str, ...]:
    if isinstance(items, (str, bytes)):
        raise ValueError(f"{field} must be a collection of non-empty strings, not a single string")
    try:
        values = tuple(items)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{field} must be a collection of non-empty strings") from exc
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} entries must be non-empty strings")
    # Preserve valid caller text literally; validation must not silently rewrite
    # assumptions or warnings that carry physical meaning.
    return values


@dataclass(frozen=True)
class Interval:
    """Closed absolute bounds for the same quantity and unit as a result value.

    This object is deliberately non-statistical. It does not imply a confidence
    level, probability distribution, standard uncertainty or coverage factor.
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = require_number(self.lower, "engineering interval lower", ValueError)
        upper = require_number(self.upper, "engineering interval upper", ValueError)
        assert lower is not None and upper is not None
        if lower > upper:
            raise ValueError("engineering interval lower bound must be <= upper bound")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    def contains(self, value: float) -> bool:
        number = require_number(value, "engineering interval value", ValueError)
        assert number is not None
        return self.lower <= number <= self.upper

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class SourceRef:
    """Traceable origin declared for an engineering input or model parameter."""

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
    """A scalar result with caller-declared traceability and limitations.

    Low-level deterministic equations may return plain floats. This wrapper is
    for user-facing composed results where provenance, assumptions, warnings or
    bounds must remain attached to the value.

    ``confidence`` is a qualitative label supplied by the caller; PyExtrusion
    does not infer or certify it. ``uncertainty`` contains absolute lower and
    upper bounds in the same unit as ``value``. ``uncertainty=None`` means that
    no bounds were supplied, never that uncertainty is zero.
    """

    value: float | None
    unit: str
    estimate_kind: EstimateKind
    confidence: Confidence
    uncertainty: Interval | None = None
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[SourceRef, ...] = ()
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        value: float | None = None
        if self.value is not None:
            validated = require_number(self.value, "engineering result value", ValueError)
            assert validated is not None
            value = validated
            object.__setattr__(self, "value", validated)

        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("engineering result unit must be a non-empty string")
        object.__setattr__(self, "unit", self.unit.strip())

        if self.estimate_kind not in {"direct", "derived", "indicator", "calibrated_prediction"}:
            raise ValueError(f"unsupported engineering estimate kind: {self.estimate_kind!r}")
        if self.confidence not in {"high", "medium", "low"}:
            raise ValueError(f"unsupported engineering confidence: {self.confidence!r}")

        if self.uncertainty is not None and not isinstance(self.uncertainty, Interval):
            raise ValueError("engineering result uncertainty must be an Interval when provided")
        if value is None and self.uncertainty is not None:
            raise ValueError("an unavailable engineering result cannot carry numeric uncertainty bounds")
        if value is not None and self.uncertainty is not None and not self.uncertainty.contains(value):
            raise ValueError("engineering result value must lie within its absolute uncertainty bounds")

        if value is None:
            if not isinstance(self.unavailable_reason, str) or not self.unavailable_reason.strip():
                raise ValueError("an unavailable engineering result requires a non-empty unavailable_reason")
            object.__setattr__(self, "unavailable_reason", self.unavailable_reason.strip())
        elif self.unavailable_reason is not None:
            raise ValueError("unavailable_reason is only valid when engineering result value is None")

        object.__setattr__(self, "assumptions", _validated_text_items(self.assumptions, "engineering assumptions"))
        object.__setattr__(self, "warnings", _validated_text_items(self.warnings, "engineering warnings"))

        provenance = tuple(self.provenance)
        if any(not isinstance(item, SourceRef) for item in provenance):
            raise ValueError("engineering result provenance entries must be SourceRef instances")
        object.__setattr__(self, "provenance", provenance)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
