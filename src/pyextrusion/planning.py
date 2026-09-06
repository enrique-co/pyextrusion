from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .api import calculate_case, calculate_process
from .errors import InvalidPlanningRequestError, InvalidProductionInputError
from ._strict import finite_product, require_int, require_number
from .models import CalculationResult, PlanningCase, PressSpec, ProcessResult, StudyCase

PlanningMode = Literal["bars", "kg", "m", "billets", "minutes", "hours"]
PlanningInputCase = PlanningCase | StudyCase


@dataclass(frozen=True)
class PlanningRequest:
    """Explicit operational target or available press-time window."""

    mode: PlanningMode
    value: float

    @classmethod
    def bars(cls, value: int) -> "PlanningRequest":
        return cls("bars", value)

    @classmethod
    def kg(cls, value: float) -> "PlanningRequest":
        return cls("kg", value)

    @classmethod
    def metres(cls, value: float) -> "PlanningRequest":
        return cls("m", value)

    @classmethod
    def meters(cls, value: float) -> "PlanningRequest":
        return cls.metres(value)

    @classmethod
    def billets(cls, value: int) -> "PlanningRequest":
        return cls("billets", value)

    @classmethod
    def minutes(cls, value: float) -> "PlanningRequest":
        return cls("minutes", value)

    @classmethod
    def hours(cls, value: float) -> "PlanningRequest":
        return cls("hours", value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanningResult:
    """Operational planning output built on a quantity-free ProcessResult."""

    request: PlanningRequest
    process: ProcessResult
    request_fulfilled: bool
    calculation: CalculationResult | None
    normalized_target_bars: int | None
    requested_billets: int | None
    available_time_min: float | None
    planned_billets: int
    planned_bars: int
    planned_good_m: float
    planned_good_kg: float
    time_used_min: float
    time_remaining_min: float | None
    additional_time_for_next_billet_min: float | None
    complete_billets_only: bool
    warnings: tuple[str, ...] = ()

    @property
    def press_name(self) -> str:
        return self.process.press_name

    @property
    def process_viable(self) -> bool:
        return self.process.viable

    @property
    def process_supported(self) -> bool:
        return self.process.supported

    @property
    def reference(self) -> ProcessResult:
        """Deprecated compatibility alias for ``process``."""
        return self.process

    @property
    def planned_hours(self) -> float:
        return self.time_used_min / 60.0

    @property
    def bars_per_billet(self) -> int:
        return self.process.bars_per_billet

    @property
    def billets_per_pull(self) -> int:
        return self.process.billets_per_pull

    @property
    def planned_pulls(self) -> int:
        return self.calculation.n_pulls if self.calculation is not None else 0

    @property
    def recommended_configuration(self) -> str | None:
        return self.process.recommended_configuration

    @property
    def billet_length_mm(self) -> float:
        return self.process.billet_length_mm

    @property
    def recommended_billet_length_mm(self) -> int:
        return self.process.recommended_billet_length_mm

    @property
    def table_occupancy_length_m(self) -> float:
        return self.process.table_occupancy_length_m

    @property
    def planned_fixed_scrap_kg(self) -> float:
        return self.calculation.fixed_scrap_kg if self.calculation is not None else 0.0

    @property
    def planned_total_scrap_kg(self) -> float:
        return self.calculation.global_scrap_kg if self.calculation is not None else 0.0

    @property
    def planned_total_scrap_pct(self) -> float:
        return self.calculation.global_scrap_pct if self.calculation is not None else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "press_name": self.press_name,
            "request": self.request.to_dict(),
            "process_supported": self.process_supported,
            "process_viable": self.process_viable,
            "request_fulfilled": self.request_fulfilled,
            "normalized_target_bars": self.normalized_target_bars,
            "requested_billets": self.requested_billets,
            "available_time_min": self.available_time_min,
            "planned_billets": self.planned_billets,
            "planned_pulls": self.planned_pulls,
            "billets_per_pull": self.billets_per_pull,
            "planned_bars": self.planned_bars,
            "planned_good_m": self.planned_good_m,
            "planned_good_kg": self.planned_good_kg,
            "time_used_min": self.time_used_min,
            "planned_hours": self.planned_hours,
            "time_remaining_min": self.time_remaining_min,
            "additional_time_for_next_billet_min": self.additional_time_for_next_billet_min,
            "complete_billets_only": self.complete_billets_only,
            "bars_per_billet": self.bars_per_billet,
            "recommended_configuration": self.recommended_configuration,
            "billet_length_mm": self.billet_length_mm,
            "recommended_billet_length_mm": self.recommended_billet_length_mm,
            "table_occupancy_length_m": self.table_occupancy_length_m,
            "planned_fixed_scrap_kg": self.planned_fixed_scrap_kg,
            "planned_total_scrap_kg": self.planned_total_scrap_kg,
            "planned_total_scrap_pct": self.planned_total_scrap_pct,
            "warnings": list(self.warnings),
            "process": self.process.to_dict(),
            "reference": self.process.to_dict(),  # deprecated JSON alias
            "calculation": self.calculation.to_dict() if self.calculation is not None else None,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


def validate_planning_request(request: PlanningRequest) -> None:
    valid_modes = {"bars", "kg", "m", "billets", "minutes", "hours"}
    if request.mode not in valid_modes:
        raise InvalidPlanningRequestError(
            "planning mode must be one of: bars, kg, m, billets, minutes, hours"
        )
    if request.mode in {"bars", "billets"}:
        require_int(request.value, f"planning.{request.mode}", InvalidPlanningRequestError, minimum=1)
    else:
        require_number(
            request.value,
            f"planning.{request.mode}",
            InvalidPlanningRequestError,
            minimum=0.0,
            exclusive_minimum=True,
        )


def _planning_case(case: PlanningInputCase) -> PlanningCase:
    return case if isinstance(case, PlanningCase) else case.to_planning_case()


def _operational_case(case: PlanningCase, bars_requested: int) -> StudyCase:
    # This conversion is used only once a real operational quantity exists.
    return case.to_study_case(int(bars_requested), supplement_10_pct=False)


def _request_warnings(case: PlanningInputCase) -> list[str]:
    warnings: list[str] = []
    if isinstance(case, StudyCase):
        warnings.append(
            "StudyCase planning compatibility is deprecated; prefer PlanningCase(press + profile + ProcessSpec)."
        )
        if case.production.supplement_10_pct:
            warnings.append(
                "Planning uses the explicit operational target; supplement_10_pct is not applied."
            )
    return warnings


def _normalized_bars(case: PlanningCase, request: PlanningRequest) -> int:
    cut_m = case.process.cut_length_mm / 1000.0
    bar_kg = finite_product(
        cut_m,
        case.profile.linear_weight_kg_m,
        "planning.bar_kg",
        InvalidPlanningRequestError,
    )
    if request.mode == "bars":
        return int(request.value)
    if request.mode == "kg":
        return math.ceil(float(request.value) / bar_kg)
    if request.mode == "m":
        return math.ceil(float(request.value) / cut_m)
    raise InvalidPlanningRequestError(
        "internal planning normalization requires bars, kg or m mode"
    )


def _time_for_billets(press: PressSpec, process: ProcessResult, billets: int) -> float:
    if billets <= 0:
        return 0.0
    dead_events = max(billets - 1, 0)
    if process.profiles_per_billet == 2:
        dead_events += billets
    total = billets * process.extrusion_time_per_billet_min + dead_events * press.dead_time_sec / 60.0
    if not math.isfinite(total):
        raise InvalidPlanningRequestError(
            "planning time result is outside the supported finite numeric range"
        )
    return total


def _empty_result(
    request: PlanningRequest,
    process: ProcessResult,
    *,
    warnings: list[str],
    requested_billets: int | None = None,
    available_time_min: float | None = None,
    additional_time: float | None = None,
) -> PlanningResult:
    return PlanningResult(
        request=request,
        process=process,
        request_fulfilled=False,
        calculation=None,
        normalized_target_bars=None,
        requested_billets=requested_billets,
        available_time_min=available_time_min,
        planned_billets=0,
        planned_bars=0,
        planned_good_m=0.0,
        planned_good_kg=0.0,
        time_used_min=0.0,
        time_remaining_min=available_time_min,
        additional_time_for_next_billet_min=additional_time,
        complete_billets_only=True,
        warnings=tuple(warnings),
    )


def _plan_for_bars(
    press: PressSpec,
    case: PlanningCase,
    request: PlanningRequest,
    bars_target: int,
    *,
    process: ProcessResult,
    requested_billets: int | None = None,
    warnings: list[str] | None = None,
) -> PlanningResult:
    try:
        calculation = calculate_case(press, _operational_case(case, bars_target))
    except (InvalidProductionInputError, OverflowError) as exc:
        raise InvalidPlanningRequestError(
            f"planning target is outside the supported numeric range: {exc}"
        ) from exc
    cut_m = case.process.cut_length_mm / 1000.0
    planned_bars = calculation.bars_manufactured if calculation.viable else 0
    planned_billets = calculation.billets if calculation.viable else 0
    return PlanningResult(
        request=request,
        process=process,
        request_fulfilled=calculation.viable,
        calculation=calculation if calculation.viable else None,
        normalized_target_bars=bars_target,
        requested_billets=requested_billets,
        available_time_min=None,
        planned_billets=planned_billets,
        planned_bars=planned_bars,
        planned_good_m=planned_bars * cut_m,
        planned_good_kg=calculation.good_kg_manufactured if calculation.viable else 0.0,
        time_used_min=calculation.total_time_min if calculation.viable else 0.0,
        time_remaining_min=None,
        additional_time_for_next_billet_min=None,
        complete_billets_only=True,
        warnings=tuple(warnings or ()),
    )


def _calculate_exact_billet_plan(
    press: PressSpec,
    case: PlanningCase,
    request: PlanningRequest,
    process: ProcessResult,
    *,
    warnings: list[str],
) -> PlanningResult:
    requested_billets = int(request.value)
    if not process.viable or process.bars_per_billet <= 0:
        return _empty_result(
            request,
            process,
            warnings=warnings,
            requested_billets=requested_billets,
        )
    bars_target = requested_billets * process.bars_per_billet
    result = _plan_for_bars(
        press,
        case,
        request,
        bars_target,
        process=process,
        requested_billets=requested_billets,
        warnings=warnings,
    )
    if result.calculation is not None and result.calculation.billets != requested_billets:
        raise RuntimeError(
            "planning invariant failed: exact billet request did not produce the requested billet count"
        )
    return result


def _calculate_time_window_plan(
    press: PressSpec,
    case: PlanningCase,
    request: PlanningRequest,
    process: ProcessResult,
    *,
    warnings: list[str],
) -> PlanningResult:
    raw_available = require_number(
        request.value,
        f"planning.{request.mode}",
        InvalidPlanningRequestError,
        minimum=0.0,
        exclusive_minimum=True,
    )
    assert raw_available is not None
    available = (
        finite_product(
            raw_available,
            60.0,
            "planning.available_time_min",
            InvalidPlanningRequestError,
        )
        if request.mode == "hours"
        else raw_available
    )

    if not process.viable or process.bars_per_billet <= 0:
        return _empty_result(
            request,
            process,
            warnings=warnings,
            available_time_min=available,
        )

    d = press.dead_time_sec / 60.0
    dead_events_per_billet = 2 if process.profiles_per_billet == 2 else 1
    denominator = process.extrusion_time_per_billet_min + dead_events_per_billet * d
    estimated = math.floor((available + d) / denominator) if denominator > 0 else 0
    billets = max(0, estimated)

    time_used = _time_for_billets(press, process, billets)
    while billets > 0 and time_used > available + 1e-9:
        billets -= 1
        time_used = _time_for_billets(press, process, billets)
    while _time_for_billets(press, process, billets + 1) <= available + 1e-9:
        billets += 1
        time_used = _time_for_billets(press, process, billets)

    next_time = _time_for_billets(press, process, billets + 1)
    additional = max(0.0, next_time - available)

    if billets == 0:
        return _empty_result(
            request,
            process,
            warnings=warnings,
            available_time_min=available,
            additional_time=additional,
        )

    bars_target = billets * process.bars_per_billet
    planned = _plan_for_bars(
        press,
        case,
        request,
        bars_target,
        process=process,
        warnings=warnings,
    )
    if planned.calculation is None:
        return _empty_result(
            request,
            process,
            warnings=warnings,
            available_time_min=available,
            additional_time=additional,
        )
    if planned.planned_billets != billets:
        raise RuntimeError(
            "planning invariant failed: time-window order changed the resolved billet count"
        )

    return PlanningResult(
        request=request,
        process=process,
        request_fulfilled=True,
        calculation=planned.calculation,
        normalized_target_bars=bars_target,
        requested_billets=None,
        available_time_min=available,
        planned_billets=billets,
        planned_bars=planned.planned_bars,
        planned_good_m=planned.planned_good_m,
        planned_good_kg=planned.planned_good_kg,
        time_used_min=time_used,
        time_remaining_min=max(0.0, available - time_used),
        additional_time_for_next_billet_min=additional,
        complete_billets_only=True,
        warnings=tuple(warnings),
    )


def calculate_planning(
    press: PressSpec,
    case: PlanningInputCase,
    request: PlanningRequest,
) -> PlanningResult:
    """Calculate an operational plan from a quantity-free process definition.

    ``PlanningCase`` is the preferred API. ``StudyCase`` remains accepted as a
    compatibility bridge, but the planning engine first converts it into a
    quantity-free process and never uses its bars_requested value to resolve
    process geometry.
    """

    validate_planning_request(request)
    warnings = _request_warnings(case)
    planning_case = _planning_case(case)

    # v0.14: genuine quantity-free process resolution. No fictitious one-bar
    # StudyCase is created to determine billet, cuts or configuration.
    process = calculate_process(press, planning_case)

    if request.mode in {"bars", "kg", "m"}:
        if not process.viable:
            return _empty_result(request, process, warnings=warnings)
        bars_target = _normalized_bars(planning_case, request)
        return _plan_for_bars(
            press,
            planning_case,
            request,
            bars_target,
            process=process,
            warnings=warnings,
        )
    if request.mode == "billets":
        return _calculate_exact_billet_plan(
            press, planning_case, request, process, warnings=warnings
        )
    return _calculate_time_window_plan(
        press, planning_case, request, process, warnings=warnings
    )
