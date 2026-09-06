from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from .demand import AnnualDemandSpec
from .errors import PyExtrusionError
from .io import load_annual_demand_json, load_case_json, load_planning_case_json, load_press_json, load_study_json, load_production_sequence_json
from .models import PlanningCase, PressSpec, ProcessSpec, ProductionSpec, ProfileSpec, StudyCase, StudyInput


@dataclass(frozen=True)
class ValidationMessage:
    level: str
    field: str
    message: str
    code: str | None = None


def validate_press(press: PressSpec) -> tuple[ValidationMessage, ...]:
    out: list[ValidationMessage] = []
    checks = [
        (isinstance(press.name, str) and bool(press.name.strip()), "press.name", "must not be empty"),
        (math.isfinite(press.table_length_m) and 10 <= press.table_length_m <= 100, "press.table_length_m", "must be between 10 and 100 m"),
        (math.isfinite(press.container_diameter_mm) and press.container_diameter_mm > 0, "press.container_diameter_mm", "must be finite and > 0"),
        (math.isfinite(press.billet_diameter_mm) and press.billet_diameter_mm > 0, "press.billet_diameter_mm", "must be finite and > 0"),
        (math.isfinite(press.billet_min_length_mm) and 100 <= press.billet_min_length_mm <= 3000, "press.billet_min_length_mm", "must be between 100 and 3000 mm"),
        (math.isfinite(press.billet_max_length_mm) and 100 <= press.billet_max_length_mm <= 3000, "press.billet_max_length_mm", "must be between 100 and 3000 mm"),
        (press.billet_max_length_mm >= press.billet_min_length_mm, "press.billet_max_length_mm", "must be >= billet_min_length_mm"),
        (math.isfinite(press.dead_time_sec) and 5 <= press.dead_time_sec <= 30, "press.dead_time_sec", "must be between 5 and 30 s"),
        (math.isfinite(press.density_kg_m3) and press.density_kg_m3 > 0, "press.density_kg_m3", "must be finite and > 0"),
        (press.container_diameter_mm > press.billet_diameter_mm, "press.container_diameter_mm", "must be greater than billet_diameter_mm"),
    ]
    if press.press_force_t is not None:
        checks.append((press.press_force_t > 0, "press.press_force_t", "must be > 0 when provided"))
    if press.nominal_size_in is not None:
        checks.append((isinstance(press.nominal_size_in, int) and not isinstance(press.nominal_size_in, bool) and 6 <= press.nominal_size_in <= 16, "press.nominal_size_in", "must be an integer from 6 to 16"))
    if press.target_net_productivity_kg_h is not None:
        checks.append(
            (
                press.target_net_productivity_kg_h > 0,
                "press.target_net_productivity_kg_h",
                "must be > 0 when provided or inferred",
            )
        )

    for ok, field, message in checks:
        if not ok:
            warning = "normally" in message
            out.append(
                ValidationMessage(
                    "warning" if warning else "error",
                    field,
                    message,
                    None if warning else "PX1001",
                )
            )

    for saw_name, saw_value in {
        "billet_mm": press.saws.billet_mm,
        "puller_mm": press.saws.puller_mm,
        "final_mm": press.saws.final_mm,
    }.items():
        if not math.isfinite(saw_value) or not (saw_value == 0 or 3 <= saw_value <= 10):
            out.append(ValidationMessage("error", f"press.saws.{saw_name}", "must be 0 mm or between 3 and 10 mm", "PX1001"))
    if press.billet_area_m2_override is not None:
        out.append(
            ValidationMessage(
                "warning",
                "press.billet_area_m2_override",
                "legacy field is ignored by calculation model v2.4; billet area is derived from billet_diameter_mm. Use billet_kg_per_mm_override for a measured mass coefficient",
                None,
            )
        )
    if press.billet_kg_per_mm_override is not None and press.billet_kg_per_mm_override <= 0:
        out.append(
            ValidationMessage(
                "error", "press.billet_kg_per_mm_override", "must be > 0", "PX1001"
            )
        )
    return tuple(out)


def _validate_profile(profile: ProfileSpec) -> list[ValidationMessage]:
    out: list[ValidationMessage] = []
    fields = [
        (profile.linear_weight_kg_m > 0, "profile.linear_weight_kg_m", "must be > 0"),
        (profile.exits >= 1, "profile.exits", "must be >= 1"),
        (
            profile.profile_type in {"solid", "hollow"},
            "profile.profile_type",
            "must be one of: solid, plate, hollow, tubular",
        ),
    ]
    for ok, field, message in fields:
        if not ok:
            out.append(ValidationMessage("error", field, message, "PX1002"))
    if profile.section_per_exit_m2 is not None and profile.section_per_exit_m2 <= 0:
        out.append(
            ValidationMessage(
                "error", "profile.section_per_exit_m2", "must be > 0", "PX1002"
            )
        )
    return out


def _validate_process(process: ProcessSpec) -> list[ValidationMessage]:
    out: list[ValidationMessage] = []
    fields = [
        (process.exit_speed_m_min is None or 1 <= process.exit_speed_m_min <= 100, "process.exit_speed_m_min", "must be between 1 and 100 m/min when provided"),
        (1000 <= process.cut_length_mm <= 15000, "process.cut_length_mm", "must be between 1000 and 15000 mm"),
        (process.front_scrap_m >= 0, "process.front_scrap_m", "must be >= 0"),
        (process.complexity in {"normal", "medium", "high"}, "process.complexity", "must be normal, medium or high"),
    ]
    for ok, field, message in fields:
        if not ok:
            out.append(ValidationMessage("error", field, message, "PX1003"))
    if (process.exit_speed_m_min is None) == (process.ram_speed_mm_s is None):
        out.append(ValidationMessage("error", "process.speed", "define exactly one of exit_speed_m_min or ram_speed_mm_s", "PX1003"))
    if process.ram_speed_mm_s is not None and (not math.isfinite(process.ram_speed_mm_s) or process.ram_speed_mm_s <= 0):
        out.append(ValidationMessage("error", "process.ram_speed_mm_s", "must be finite and > 0", "PX1003"))
    if process.cuts is not None and process.cuts < 1:
        out.append(ValidationMessage("error", "process.cuts", "must be >= 1", "PX1003"))
    if process.butt_mm is not None and process.butt_mm < 0:
        out.append(ValidationMessage("error", "process.butt_mm", "must be >= 0", "PX1003"))
    if process.multi_billet_front_scrap_m is not None and process.multi_billet_front_scrap_m < 0:
        out.append(ValidationMessage("error", "process.multi_billet_front_scrap_m", "must be >= 0", "PX1003"))
    return out


def _validate_production(production: ProductionSpec) -> list[ValidationMessage]:
    out: list[ValidationMessage] = []
    fields = [
        (production.exit_speed_m_min is None or 1 <= production.exit_speed_m_min <= 100, "production.exit_speed_m_min", "must be between 1 and 100 m/min when provided"),
        (1000 <= production.cut_length_mm <= 15000, "production.cut_length_mm", "must be between 1000 and 15000 mm"),
        (production.bars_requested >= 1, "production.bars_requested", "must be >= 1"),
        (production.front_scrap_m >= 0, "production.front_scrap_m", "must be >= 0"),
        (
            production.complexity in {"normal", "medium", "high"},
            "production.complexity",
            "must be normal, medium or high",
        ),
        (
            isinstance(production.supplement_10_pct, bool),
            "production.supplement_10_pct",
            "must be true or false",
        ),
    ]
    for ok, field, message in fields:
        if not ok:
            out.append(ValidationMessage("error", field, message, "PX1003"))
    if (production.exit_speed_m_min is None) == (production.ram_speed_mm_s is None):
        out.append(ValidationMessage("error", "production.speed", "define exactly one of exit_speed_m_min or ram_speed_mm_s", "PX1003"))
    if production.ram_speed_mm_s is not None and (not math.isfinite(production.ram_speed_mm_s) or production.ram_speed_mm_s <= 0):
        out.append(ValidationMessage("error", "production.ram_speed_mm_s", "must be finite and > 0", "PX1003"))
    if production.cuts is not None and production.cuts < 1:
        out.append(ValidationMessage("error", "production.cuts", "must be >= 1", "PX1003"))
    if production.butt_mm is not None and production.butt_mm < 0:
        out.append(ValidationMessage("error", "production.butt_mm", "must be >= 0", "PX1003"))
    if production.multi_billet_front_scrap_m is not None and production.multi_billet_front_scrap_m < 0:
        out.append(
            ValidationMessage(
                "error",
                "production.multi_billet_front_scrap_m",
                "must be >= 0",
                "PX1003",
            )
        )
    return out


def validate_case(case: StudyCase) -> tuple[ValidationMessage, ...]:
    return tuple(_validate_profile(case.profile) + _validate_production(case.production))


def validate_planning_case(case: PlanningCase) -> tuple[ValidationMessage, ...]:
    return tuple(_validate_profile(case.profile) + _validate_process(case.process))


def validate_study(study: StudyInput) -> tuple[ValidationMessage, ...]:
    out = list(validate_press(study.press)) + _validate_profile(study.profile) + _validate_production(study.to_case().production)
    if study.cut_length_mm > study.press.table_length_m * 1000:
        out.append(ValidationMessage("error", "production.cut_length_mm", "must not exceed press table length", "PX1003"))
    if study.front_scrap_m >= study.press.table_length_m:
        out.append(ValidationMessage("error", "production.front_scrap_m", "must be less than press table length", "PX1003"))
    if study.multi_billet_front_scrap_m is not None and study.multi_billet_front_scrap_m >= study.press.table_length_m:
        out.append(ValidationMessage("error", "production.multi_billet_front_scrap_m", "must be less than press table length", "PX1003"))
    return tuple(out)


def validate_annual_demand(demand: AnnualDemandSpec) -> tuple[ValidationMessage, ...]:
    out: list[ValidationMessage] = []
    if demand.unit not in {"kg", "m", "bars"}:
        out.append(
            ValidationMessage(
                "error", "annual_demand.unit", "must be kg, m or bars", "PX1006"
            )
        )
    if demand.unit == "bars":
        if isinstance(demand.value, bool) or not isinstance(demand.value, int) or demand.value < 1:
            out.append(ValidationMessage("error", "annual_demand.value", "must be a positive integer for bars", "PX1006"))
    elif isinstance(demand.value, bool) or not isinstance(demand.value, (int, float)) or not math.isfinite(float(demand.value)) or float(demand.value) <= 0:
        out.append(ValidationMessage("error", "annual_demand.value", "must be finite and > 0", "PX1006"))
    return tuple(out)


def _validate_loader(loader, path: str | Path, validator) -> tuple[ValidationMessage, ...]:
    try:
        obj = loader(path)
    except PyExtrusionError as exc:
        return (ValidationMessage("error", "input", str(exc), exc.code),)
    except ValueError as exc:
        return (ValidationMessage("error", "input", str(exc), None),)
    return validator(obj)


def validate_press_json(path: str | Path) -> tuple[ValidationMessage, ...]:
    return _validate_loader(load_press_json, path, validate_press)


def validate_case_json(path: str | Path) -> tuple[ValidationMessage, ...]:
    return _validate_loader(load_case_json, path, validate_case)


def validate_planning_case_json(path: str | Path) -> tuple[ValidationMessage, ...]:
    return _validate_loader(load_planning_case_json, path, validate_planning_case)


def validate_study_json(path: str | Path) -> tuple[ValidationMessage, ...]:
    return _validate_loader(load_study_json, path, validate_study)


def validate_annual_demand_json(path: str | Path) -> tuple[ValidationMessage, ...]:
    return _validate_loader(load_annual_demand_json, path, validate_annual_demand)


def validate_production_sequence_json(path: str | Path) -> tuple[ValidationMessage, ...]:
    try:
        load_production_sequence_json(path)
    except PyExtrusionError as exc:
        return (ValidationMessage("error", "input", str(exc), exc.code),)
    except ValueError as exc:
        return (ValidationMessage("error", "input", str(exc), None),)
    return ()
