from __future__ import annotations

import math
from dataclasses import dataclass, asdict, replace
from typing import Any, Literal

from .core import calculate
from .models import CalculationResult, PressSpec, ProfileSpec, StudyCase
from .errors import InvalidAnnualDemandError, InvalidProfileInputError, InvalidProductionInputError
from ._strict import require_bool, require_int, require_number

DemandUnit = Literal["kg", "m", "bars"]


@dataclass(frozen=True)
class AnnualDemandSpec:
    """Annual demand supplied in kg/year, metres/year, or bars/year."""
    unit: DemandUnit
    value: float

    def __post_init__(self) -> None:
        if self.unit not in {"kg", "m", "bars"}:
            raise InvalidAnnualDemandError("annual demand unit must be one of: kg, m, bars")
        if self.unit == "bars":
            require_int(self.value, "annual_demand.value", InvalidAnnualDemandError, minimum=1)
        else:
            require_number(self.value, "annual_demand.value", InvalidAnnualDemandError, minimum=0.0, exclusive_minimum=True)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedAnnualDemand:
    """Base and effective annual demand representations under the PyExtrusion v2.4 model."""
    source_unit: DemandUnit
    source_value: float
    supplement_10_pct: bool
    supplement_factor: float
    adjusted_source_value: float
    base_kg_target: float
    base_meters_target: float
    base_bars_target: int
    kg_target: float
    meters_target: float
    bars_target: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnnualCalculationResult:
    demand: AnnualDemandSpec
    normalized: NormalizedAnnualDemand
    calculation: CalculationResult
    billets_annual: int
    hours_annual: float

    @property
    def hours_estimated(self) -> float:
        return self.hours_annual

    def to_dict(self) -> dict[str, Any]:
        return {
            "demand": self.demand.to_dict(),
            "normalized": self.normalized.to_dict(),
            "billets_annual": self.billets_annual,
            "hours_annual": self.hours_annual,
            "hours_estimated": self.hours_estimated,
            "calculation": self.calculation.to_dict(),
        }

    def to_json(self, *, indent: int | None = None) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


def _normalize(profile: ProfileSpec, cut_m: float, unit: DemandUnit, value: float) -> tuple[float, float, int]:
    if unit == "kg":
        kg = float(value)
        metres = kg / profile.linear_weight_kg_m
        bars = math.ceil(metres / cut_m)
    elif unit == "m":
        metres = float(value)
        kg = metres * profile.linear_weight_kg_m
        bars = math.ceil(metres / cut_m)
    else:
        bars = math.ceil(value)
        metres = bars * cut_m
        kg = metres * profile.linear_weight_kg_m
    return kg, metres, bars


def normalize_annual_demand(
    profile: ProfileSpec,
    cut_length_mm: float,
    demand: AnnualDemandSpec,
    *,
    supplement_10_pct: bool = False,
) -> NormalizedAnnualDemand:
    """Apply optional 10% supplement before normalizing annual demand (PyExtrusion v2.4)."""
    if demand.unit not in {"kg", "m", "bars"}:
        raise InvalidAnnualDemandError("annual demand unit must be one of: kg, m, bars")
    if demand.unit == "bars":
        require_int(demand.value, "annual_demand.value", InvalidAnnualDemandError, minimum=1)
    else:
        require_number(demand.value, "annual_demand.value", InvalidAnnualDemandError, minimum=0.0, exclusive_minimum=True)
    require_number(profile.linear_weight_kg_m, "profile.linear_weight_kg_m", InvalidProfileInputError, minimum=0.0, exclusive_minimum=True)
    require_number(cut_length_mm, "cut_length_mm", InvalidProductionInputError, minimum=1000.0, maximum=15000.0)
    require_bool(supplement_10_pct, "supplement_10_pct", InvalidAnnualDemandError)

    cut_m = cut_length_mm / 1000.0
    factor = 1.10 if supplement_10_pct else 1.00
    adjusted = float(demand.value) * factor
    base_kg, base_m, base_bars = _normalize(profile, cut_m, demand.unit, float(demand.value))
    kg, metres, bars = _normalize(profile, cut_m, demand.unit, adjusted)
    return NormalizedAnnualDemand(
        source_unit=demand.unit, source_value=float(demand.value),
        supplement_10_pct=supplement_10_pct, supplement_factor=factor,
        adjusted_source_value=adjusted,
        base_kg_target=base_kg, base_meters_target=base_m, base_bars_target=base_bars,
        kg_target=kg, meters_target=metres, bars_target=bars,
    )


def calculate_annual_demand(press: PressSpec, case: StudyCase, demand: AnnualDemandSpec) -> AnnualCalculationResult:
    normalized = normalize_annual_demand(
        case.profile, case.production.cut_length_mm, demand,
        supplement_10_pct=case.production.supplement_10_pct,
    )
    # Preserve base-vs-effective demand exactly. The effective override avoids
    # applying 10% after an intermediate bar rounding when the source demand
    # was expressed in kg or metres.
    study = case.with_production(bars_requested=normalized.base_bars_target).to_study_input(press)
    study = replace(study, effective_bars_target_override=normalized.bars_target)
    calculation = calculate(study)
    return AnnualCalculationResult(
        demand=demand, normalized=normalized, calculation=calculation,
        billets_annual=calculation.billets,
        hours_annual=calculation.total_time_min / 60.0,
    )
