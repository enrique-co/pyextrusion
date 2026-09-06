from __future__ import annotations

from collections.abc import Iterable

from .core import calculate, calculate_process as _calculate_process
from .models import (
    CalculationResult,
    ComparisonResult,
    Complexity,
    PressSpec,
    PlanningCase,
    ProcessResult,
    ProductionSpec,
    ProfileSpec,
    ProfileType,
    StudyCase,
    StudyInput,
)


def calculate_case(press: PressSpec, case: StudyCase) -> CalculationResult:
    """Run a reusable StudyCase on one press."""
    return calculate(case.to_study_input(press))


def calculate_process(press: PressSpec, case: PlanningCase) -> ProcessResult:
    """Evaluate Press + Profile + ProcessSpec without any production quantity."""
    return _calculate_process(case.to_process_input(press))


def compare_presses(presses: Iterable[PressSpec], case: StudyCase) -> ComparisonResult:
    """Evaluate one case on several presses. Results include the orientative v2.4 productivity index; no final industrial decision is made automatically."""
    press_tuple = tuple(presses)
    if not press_tuple:
        raise ValueError("compare_presses requires at least one press")
    return ComparisonResult(tuple(calculate_case(press, case) for press in press_tuple))


def calculate_simple(
    press: PressSpec,
    *,
    linear_weight_kg_m: float,
    exits: int,
    exit_speed_m_min: float | None = None,
    cut_length_mm: float,
    bars_requested: int,
    profile_type: ProfileType | None = None,
    front_scrap_m: float = 0.0,
    complexity: Complexity = "normal",
    section_per_exit_m2: float | None = None,
    cuts: int | None = None,
    butt_mm: float | None = None,
    multi_billet_front_scrap_m: float | None = None,
    supplement_10_pct: bool = False,
    ram_speed_mm_s: float | None = None,
) -> CalculationResult:
    """Low-friction API backed by the same deterministic engine as StudyInput."""
    case = StudyCase(
        profile=ProfileSpec(
            linear_weight_kg_m=linear_weight_kg_m,
            exits=exits,
            profile_type=profile_type,
            section_per_exit_m2=section_per_exit_m2,
        ),
        production=ProductionSpec(
            exit_speed_m_min=exit_speed_m_min,
            cut_length_mm=cut_length_mm,
            bars_requested=bars_requested,
            front_scrap_m=front_scrap_m,
            complexity=complexity,
            cuts=cuts,
            butt_mm=butt_mm,
            multi_billet_front_scrap_m=multi_billet_front_scrap_m,
            supplement_10_pct=supplement_10_pct,
            ram_speed_mm_s=ram_speed_mm_s,
        ),
    )
    return calculate_case(press, case)
