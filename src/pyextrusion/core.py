from __future__ import annotations

import math
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass

from .errors import InvalidPressConfigurationError, InvalidProfileInputError, InvalidProductionInputError
from ._strict import require_bool, require_int, require_number
from .models import (
    BilletResult,
    CalculationResult,
    ConfigurationResult,
    GeometryResult,
    ProcessTraceResult,
    ProcessInput,
    ProcessResult,
    ProductionResult,
    ProductivityResult,
    ScrapResult,
    StatusResult,
    StudyInput,
    TimingResult,
    normalize_profile_type,
)

ALUMINIUM_DENSITY_KG_M3 = 2700.0
COMPLEXITY_PCT = {"normal": 0.03, "medium": 0.05, "high": 0.07}
CONFIG_PRIORITY = {
    "1_billet_1_profile": 1,
    "k_billets_1_profile": 1,
    "1_billet_2_profiles": 2,
}


@dataclass(frozen=True)
class _ResolvedProcess:
    press: object
    profile: object
    cut_m: float
    kg_m_total: float
    area_one: float
    area_total: float
    extrusion_ratio_value: float
    extrusion_ratio_status_value: str
    exit_speed_m_min: float
    ram_speed_m_min: float
    ram_speed_mm_s: float
    speed_source: str
    theoretical_cuts: int
    warnings: tuple[str, ...]
    butt_mm: float
    butt_source: str
    configurations: tuple[ConfigurationResult, ...]
    valid_configurations: tuple[ConfigurationResult, ...]
    selected: ConfigurationResult | None
    required_profiles_per_billet: int | None
    supported: bool
    unsupported_reason: str | None
    viable: bool
    selected_cuts: int
    profiles_per_billet: int
    billets_per_pull: int
    cuts_per_pull: int
    bars_per_pull: int
    bars_per_billet: int
    applied_front_scrap_m: float
    applied_front_scrap_source: str
    multi_scrap_m: float
    multi_scrap_source: str
    cuts_source: str
    table_ratio: float
    billet_ratio: float
    cuts_ratio: float
    geometric_index: float
    extrusion_time_per_billet_min: float
    recommended_billet_length_mm: int


def section_from_linear_weight(
    linear_weight_kg_m: float,
    density_kg_m3: float = ALUMINIUM_DENSITY_KG_M3,
) -> float:
    lw = require_number(linear_weight_kg_m, "linear_weight_kg_m", ValueError, minimum=0.0, exclusive_minimum=True)
    density = require_number(density_kg_m3, "density_kg_m3", ValueError, minimum=0.0, exclusive_minimum=True)
    assert lw is not None and density is not None
    return lw / density


def extrusion_ratio(
    container_area_m2: float | None = None,
    profile_total_area_m2: float | None = None,
    *,
    billet_area_m2: float | None = None,
) -> float:
    """Return the extrusion ratio using the *container bore area*.

    ``billet_area_m2`` is accepted only as a legacy keyword alias so old code
    keeps running. New code and all internal calculations use
    ``container_area_m2`` as required by the PyExtrusion model.
    """
    if container_area_m2 is None:
        container_area_m2 = billet_area_m2
    if container_area_m2 is None or profile_total_area_m2 is None:
        raise ValueError("container_area_m2 and profile_total_area_m2 are required")
    container_area = require_number(container_area_m2, "container_area_m2", ValueError, minimum=0.0, exclusive_minimum=True)
    profile_area = require_number(profile_total_area_m2, "profile_total_area_m2", ValueError, minimum=0.0, exclusive_minimum=True)
    assert container_area is not None and profile_area is not None
    ratio = container_area / profile_area
    if not math.isfinite(ratio):
        raise ValueError("extrusion ratio is outside the supported finite numeric range")
    return ratio


def ram_speed(
    exit_speed_m_min: float,
    profile_total_area_m2: float,
    container_area_m2: float | None = None,
    *,
    billet_area_m2: float | None = None,
) -> tuple[float, float]:
    """Calculate ram speed from volume constancy using container bore area."""
    if container_area_m2 is None:
        container_area_m2 = billet_area_m2
    if container_area_m2 is None:
        raise ValueError("container_area_m2 is required")
    exit_speed = require_number(exit_speed_m_min, "exit_speed_m_min", ValueError, minimum=0.0, exclusive_minimum=True)
    profile_area = require_number(profile_total_area_m2, "profile_total_area_m2", ValueError, minimum=0.0, exclusive_minimum=True)
    container_area = require_number(container_area_m2, "container_area_m2", ValueError, minimum=0.0, exclusive_minimum=True)
    assert exit_speed is not None and profile_area is not None and container_area is not None
    speed_m_min = exit_speed * (profile_area / container_area)
    speed_mm_s = speed_m_min * 1000.0 / 60.0
    if not math.isfinite(speed_m_min) or not math.isfinite(speed_mm_s):
        raise ValueError("ram speed is outside the supported finite numeric range")
    return speed_m_min, speed_mm_s


def extrusion_ratio_status(profile_type: str, ratio: float) -> str:
    """Classify RE using the documented PyExtrusion thresholds."""
    canonical = normalize_profile_type(profile_type)
    if canonical == "solid":
        if ratio < 25.0:
            return "low"
        if ratio <= 85.0:
            return "ok"
        return "high"
    if canonical == "hollow":
        if ratio < 15.0:
            return "low"
        if ratio <= 75.0:
            return "ok"
        return "high"
    raise InvalidProfileInputError(
        "Invalid profile.profile_type. Valid values: solid, plate, hollow, tubular"
    )


def _validate_process(data: ProcessInput | StudyInput) -> None:
    p, prof = data.press, data.profile

    require_number(prof.linear_weight_kg_m, "profile.linear_weight_kg_m", InvalidProfileInputError, minimum=0.0, exclusive_minimum=True)
    require_int(prof.exits, "profile.exits", InvalidProfileInputError, minimum=1)
    if prof.profile_type not in {"solid", "hollow"}:
        raise InvalidProfileInputError("Invalid profile.profile_type. Valid values: solid, plate, hollow, tubular")
    if prof.section_per_exit_m2 is not None:
        require_number(prof.section_per_exit_m2, "profile.section_per_exit_m2", InvalidProfileInputError, minimum=0.0, exclusive_minimum=True)

    if (data.exit_speed_m_min is None) == (data.ram_speed_mm_s is None):
        raise InvalidProductionInputError("process must define exactly one of exit_speed_m_min or ram_speed_mm_s")
    if data.exit_speed_m_min is not None:
        require_number(data.exit_speed_m_min, "process.exit_speed_m_min", InvalidProductionInputError, minimum=1.0, maximum=100.0)
    if data.ram_speed_mm_s is not None:
        require_number(data.ram_speed_mm_s, "process.ram_speed_mm_s", InvalidProductionInputError, minimum=0.0, exclusive_minimum=True)
    require_number(data.cut_length_mm, "process.cut_length_mm", InvalidProductionInputError, minimum=1000.0, maximum=15000.0)
    require_number(data.front_scrap_m, "process.front_scrap_m", InvalidProductionInputError, minimum=0.0)
    if data.front_scrap_m >= p.table_length_m:
        raise InvalidProductionInputError("process.front_scrap_m must be less than press.table_length_m")
    if data.multi_billet_front_scrap_m is not None:
        require_number(data.multi_billet_front_scrap_m, "process.multi_billet_front_scrap_m", InvalidProductionInputError, minimum=0.0)
        if data.multi_billet_front_scrap_m >= p.table_length_m:
            raise InvalidProductionInputError("process.multi_billet_front_scrap_m must be less than press.table_length_m")
    if data.complexity not in COMPLEXITY_PCT:
        raise InvalidProductionInputError("process.complexity must be normal, medium or high")
    if data.butt_mm is not None:
        require_number(data.butt_mm, "process.butt_mm", InvalidProductionInputError, minimum=0.0)
    if data.cuts is not None:
        require_int(data.cuts, "process.cuts", InvalidProductionInputError, minimum=1)

    if not 100.0 <= p.billet_min_length_mm <= 3000.0 or not 100.0 <= p.billet_max_length_mm <= 3000.0 or p.billet_max_length_mm < p.billet_min_length_mm:
        raise InvalidPressConfigurationError("press billet lengths must be within 100-3000 mm and min <= max")
    if not 10.0 <= p.table_length_m <= 100.0:
        raise InvalidPressConfigurationError("press.table_length_m must be between 10 and 100 m")
    if data.cut_length_mm > p.table_length_m * 1000.0:
        raise InvalidProductionInputError("process.cut_length_mm must not exceed press table length")
    if not 5.0 <= p.dead_time_sec <= 30.0:
        raise InvalidPressConfigurationError("press.dead_time_sec must be between 5 and 30 s")
    if p.container_diameter_mm <= p.billet_diameter_mm:
        raise InvalidPressConfigurationError("press.container_diameter_mm must be greater than billet_diameter_mm")
    if p.container_area_m2 <= 0 or p.billet_area_m2 <= 0 or p.billet_weight_kg_per_mm <= 0:
        raise InvalidPressConfigurationError("press geometry is invalid")
    for kerf in (p.saws.billet_mm, p.saws.puller_mm, p.saws.final_mm):
        if not (kerf == 0.0 or 3.0 <= kerf <= 10.0):
            raise InvalidPressConfigurationError("press saw kerfs must be 0 mm or between 3 and 10 mm")


def _validate(data: StudyInput) -> None:
    _validate_process(data)
    require_int(data.bars_requested, "production.bars_requested", InvalidProductionInputError, minimum=1)
    require_bool(data.supplement_10_pct, "production.supplement_10_pct", InvalidProductionInputError)
    if data.effective_bars_target_override is not None:
        require_int(data.effective_bars_target_override, "production.effective_bars_target_override", InvalidProductionInputError, minimum=1)


def _resolve_exit_and_ram_speed(data: StudyInput, extrusion_ratio_value: float, area_total: float) -> tuple[float, float, float, str]:
    if data.exit_speed_m_min is not None:
        exit_speed = float(data.exit_speed_m_min)
        try:
            ram_m_min, ram_mm_s = ram_speed(exit_speed, area_total, data.press.container_area_m2)
        except ValueError as exc:
            raise InvalidProductionInputError(
                f"derived ram speed is outside the supported finite numeric range: {exc}"
            ) from exc
        return exit_speed, ram_m_min, ram_mm_s, "exit_speed_user_value"

    assert data.ram_speed_mm_s is not None
    ram_mm_s = float(data.ram_speed_mm_s)
    ram_m_min = ram_mm_s * 60.0 / 1000.0
    exit_speed = ram_m_min * extrusion_ratio_value
    if not math.isfinite(exit_speed):
        raise InvalidProductionInputError("derived exit_speed_m_min is outside the supported finite numeric range")
    if not 1.0 <= exit_speed <= 100.0:
        raise InvalidProductionInputError(
            f"derived exit_speed_m_min={exit_speed:.6g} is outside the supported 1-100 m/min range"
        )
    return exit_speed, ram_m_min, ram_mm_s, "ram_speed_user_value"


def _billet_lengths(
    kg_m_total: float,
    length_m: float,
    kg_per_mm: float,
    butt_mm: float,
) -> tuple[float, float]:
    useful = (kg_m_total * length_m) / kg_per_mm
    return useful, useful + butt_mm


def _configuration(
    *,
    name,
    priority,
    valid,
    billets_per_configuration,
    profiles_per_configuration,
    cuts,
    front_scrap_per_billet_m,
    front_scrap_source,
    length_per_profile_m,
    length_per_billet_m,
    total_configuration_length_m,
    table_occupancy_length_m,
    billet_useful_length_mm,
    billet_length_mm,
    billets_per_pull=1,
    profiles_per_billet=1,
    cuts_per_pull=0,
    bars_per_pull=0,
    reasons=(),
) -> ConfigurationResult:
    return ConfigurationResult(
        name=name,
        priority=priority,
        valid=valid,
        billets_per_configuration=billets_per_configuration,
        profiles_per_configuration=profiles_per_configuration,
        cuts=cuts,
        front_scrap_per_billet_m=front_scrap_per_billet_m,
        front_scrap_source=front_scrap_source,
        length_per_profile_m=length_per_profile_m,
        length_per_billet_m=length_per_billet_m,
        total_configuration_length_m=total_configuration_length_m,
        table_occupancy_length_m=table_occupancy_length_m,
        billet_useful_length_mm=billet_useful_length_mm,
        billet_length_mm=billet_length_mm,
        billets_per_pull=billets_per_pull,
        profiles_per_billet=profiles_per_billet,
        cuts_per_pull=cuts_per_pull,
        bars_per_pull=bars_per_pull,
        reasons=tuple(reasons),
    )


def _fixed_scrap_score(fixed_pct: float) -> float:
    if fixed_pct <= 5.0:
        return 100.0
    if fixed_pct <= 7.0:
        return 85.0
    if fixed_pct <= 9.0:
        return 70.0
    if fixed_pct <= 12.0:
        return 50.0
    return 25.0


def _productivity_penalty(deficit_pct: float) -> float:
    if deficit_pct <= 5.0:
        return 0.0
    if deficit_pct <= 10.0:
        return 3.0
    if deficit_pct <= 15.0:
        return 7.0
    if deficit_pct <= 20.0:
        return 12.0
    return 20.0


def _productivity_rating(index: float) -> str:
    if index >= 85.0:
        return "very_favorable"
    if index >= 70.0:
        return "favorable"
    if index >= 55.0:
        return "acceptable"
    if index >= 40.0:
        return "unfavorable"
    return "highly_penalized"


def _assert_finite_result(value, path: str = "result") -> None:
    """Reject non-finite derived values before they can escape through API/JSON."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidProductionInputError(
                f"{path} is outside the supported finite numeric range; review input magnitudes"
            )
        return
    if is_dataclass(value):
        for f in dataclass_fields(value):
            _assert_finite_result(getattr(value, f.name), f"{path}.{f.name}")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_finite_result(item, f"{path}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _assert_finite_result(item, f"{path}[{index}]")


def _resolve_process(data: ProcessInput | StudyInput) -> _ResolvedProcess:
    """Resolve quantity-free geometry, billet optimisation and configuration."""
    _validate_process(data)
    p, prof = data.press, data.profile
    cut_m = data.cut_length_mm / 1000.0
    kg_m_total = prof.linear_weight_kg_m * prof.exits
    if not math.isfinite(kg_m_total) or kg_m_total <= 0:
        raise InvalidProfileInputError("profile total linear weight is outside the supported finite numeric range")

    try:
        area_one = prof.section_per_exit_m2 or section_from_linear_weight(
            prof.linear_weight_kg_m, p.density_kg_m3
        )
        area_total = area_one * prof.exits
        if not math.isfinite(area_one) or not math.isfinite(area_total) or area_one <= 0 or area_total <= 0:
            raise ValueError("profile section is outside the supported finite numeric range")
        re = extrusion_ratio(p.container_area_m2, area_total)
    except ValueError as exc:
        raise InvalidProfileInputError(f"derived profile geometry is invalid: {exc}") from exc
    re_status = extrusion_ratio_status(prof.profile_type, re)
    exit_speed_m_min, ram_m_min, ram_mm_s, speed_source = _resolve_exit_and_ram_speed(data, re, area_total)

    theoretical_cuts = math.trunc(p.table_length_m / cut_m)
    warnings: list[str] = []

    if data.butt_mm is not None:
        butt_mm = float(data.butt_mm)
        butt_source = "user_override"
    else:
        butt_mm, butt_source = p.resolve_butt_mm(prof.profile_type, kg_m_total)

    fixed_by_user = data.cuts is not None
    puller_kerf_m = p.saws.puller_mm / 1000.0
    final_kerf_m = p.saws.final_mm / 1000.0

    def _one_profile_cfg(front_scrap_m: float, source: str, *, require_multi: bool = False) -> ConfigurationResult:
        def build(n: int) -> ConfigurationResult:
            base_segment_m = n * cut_m + front_scrap_m if n >= 1 else 0.0
            per_billet_nonshared_m = (
                base_segment_m + n * final_kerf_m if n >= 1 else 0.0
            )
            shared_pull_kerf_m = puller_kerf_m + final_kerf_m
            available_for_billets_m = p.table_length_m - shared_pull_kerf_m
            k = (
                math.floor(available_for_billets_m / per_billet_nonshared_m)
                if per_billet_nonshared_m > 0 and available_for_billets_m >= 0
                else 0
            )
            full_pull_m = (
                k * per_billet_nonshared_m + shared_pull_kerf_m if k >= 1 else 0.0
            )
            physical_per_billet_m = full_pull_m / k if k >= 1 else 0.0
            useful_mm, billet_mm = (
                _billet_lengths(
                    kg_m_total,
                    physical_per_billet_m,
                    p.billet_weight_kg_per_mm,
                    butt_mm,
                )
                if n >= 1 and k >= 1 else (0.0, 0.0)
            )
            reasons: list[str] = []
            if n < 1:
                reasons.append("cuts < 1")
            if k < 1:
                reasons.append("no complete physical pull fits the table")
            if full_pull_m > p.table_length_m + 1e-12:
                reasons.append("physical pull including saw kerfs exceeds table length")
            if billet_mm < p.billet_min_length_mm:
                reasons.append("billet below minimum")
            if billet_mm > p.billet_max_length_mm:
                reasons.append("billet above maximum")
            if require_multi and k < 2:
                reasons.append("multi-billet front scrap requires billets_per_pull >= 2")
            name = "k_billets_1_profile" if k >= 2 else "1_billet_1_profile"
            cuts_per_pull = n * max(k, 0)
            return _configuration(
                name=name,
                priority=CONFIG_PRIORITY[name],
                valid=not reasons,
                billets_per_configuration=max(k, 1),
                profiles_per_configuration=1,
                cuts=n,
                front_scrap_per_billet_m=front_scrap_m,
                front_scrap_source=source,
                length_per_profile_m=base_segment_m,
                length_per_billet_m=physical_per_billet_m,
                total_configuration_length_m=full_pull_m,
                table_occupancy_length_m=full_pull_m,
                billet_useful_length_mm=useful_mm,
                billet_length_mm=billet_mm,
                billets_per_pull=max(k, 1),
                profiles_per_billet=1,
                cuts_per_pull=cuts_per_pull,
                bars_per_pull=cuts_per_pull * prof.exits,
                reasons=reasons,
            )

        if fixed_by_user:
            return build(int(data.cuts))

        candidates = [build(n) for n in range(1, theoretical_cuts + 1)]
        valid_candidates = [candidate for candidate in candidates if candidate.valid]
        if valid_candidates:
            return max(valid_candidates, key=lambda candidate: candidate.billet_length_mm)
        if not candidates:
            return build(0)
        return max(
            candidates,
            key=lambda candidate: (
                candidate.billet_length_mm <= p.billet_max_length_mm,
                candidate.billet_length_mm,
            ),
        )

    cfg_one_standard = _one_profile_cfg(data.front_scrap_m, "standard")
    one_candidates: list[ConfigurationResult] = []
    if data.multi_billet_front_scrap_m is None:
        one_candidates.append(cfg_one_standard)
        multi_scrap = data.front_scrap_m
        multi_scrap_source = "standard_fallback"
    else:
        multi_scrap = data.multi_billet_front_scrap_m
        multi_scrap_source = "user_override"
        if cfg_one_standard.billets_per_pull == 1:
            one_candidates.append(cfg_one_standard)
        cfg_multi = _one_profile_cfg(
            data.multi_billet_front_scrap_m,
            "user_override",
            require_multi=True,
        )
        one_candidates.append(cfg_multi)

    valid_one = [c for c in one_candidates if c.valid]
    if valid_one:
        cfg_one = max(valid_one, key=lambda c: c.billet_length_mm)
    else:
        cfg_one = max(
            one_candidates,
            key=lambda c: (
                c.billet_length_mm <= p.billet_max_length_mm,
                c.billet_length_mm,
            ),
        )

    def _double_profile_cfg() -> ConfigurationResult:
        def build(n: int) -> ConfigurationResult:
            base_per_profile_m = n * cut_m + data.front_scrap_m if n >= 1 else 0.0
            physical_per_profile_m = (
                base_per_profile_m
                + puller_kerf_m
                + (n + 1) * final_kerf_m
                if n >= 1 else 0.0
            )
            total_extruded_m = 2.0 * physical_per_profile_m
            useful_mm, billet_mm = (
                _billet_lengths(
                    kg_m_total,
                    total_extruded_m,
                    p.billet_weight_kg_per_mm,
                    butt_mm,
                )
                if n >= 1 else (0.0, 0.0)
            )
            reasons: list[str] = []
            if n < 1:
                reasons.append("cuts < 1")
            if physical_per_profile_m > p.table_length_m:
                reasons.append("physical profile pull including saw kerfs exceeds table length")
            if billet_mm < p.billet_min_length_mm:
                reasons.append("double-profile billet below minimum")
            if billet_mm > p.billet_max_length_mm:
                reasons.append("double-profile billet above maximum")
            return _configuration(
                name="1_billet_2_profiles",
                priority=CONFIG_PRIORITY["1_billet_2_profiles"],
                valid=not reasons,
                billets_per_configuration=1,
                profiles_per_configuration=2,
                cuts=n,
                front_scrap_per_billet_m=data.front_scrap_m,
                front_scrap_source="standard",
                length_per_profile_m=physical_per_profile_m,
                length_per_billet_m=total_extruded_m,
                total_configuration_length_m=total_extruded_m,
                table_occupancy_length_m=physical_per_profile_m,
                billet_useful_length_mm=useful_mm,
                billet_length_mm=billet_mm,
                billets_per_pull=1,
                profiles_per_billet=2,
                cuts_per_pull=n,
                bars_per_pull=n * prof.exits,
                reasons=reasons,
            )

        if fixed_by_user:
            return build(int(data.cuts))
        candidates = [build(n) for n in range(1, theoretical_cuts + 1)]
        valid_candidates = [candidate for candidate in candidates if candidate.valid]
        if valid_candidates:
            return max(valid_candidates, key=lambda candidate: candidate.billet_length_mm)
        if not candidates:
            return build(0)
        return max(
            candidates,
            key=lambda candidate: (
                candidate.billet_length_mm <= p.billet_max_length_mm,
                candidate.billet_length_mm,
            ),
        )

    cfg_double = _double_profile_cfg()
    configurations = (cfg_one, cfg_double)
    valid = tuple(cfg for cfg in configurations if cfg.valid)

    selected: ConfigurationResult | None = None
    if valid:
        selected = max(valid, key=lambda c: (c.billet_length_mm, -c.profiles_per_billet))

    def _required_unsupported_profiles() -> int | None:
        n_values = [int(data.cuts)] if fixed_by_user else list(range(1, theoretical_cuts + 1))
        best: int | None = None
        for n in n_values:
            if n < 1:
                continue
            physical_per_profile_m = (
                n * cut_m
                + data.front_scrap_m
                + puller_kerf_m
                + (n + 1) * final_kerf_m
            )
            if physical_per_profile_m > p.table_length_m:
                continue
            useful_per_profile_mm = (
                kg_m_total * physical_per_profile_m
            ) / p.billet_weight_kg_per_mm
            if useful_per_profile_mm <= 0:
                continue
            min_profiles = max(
                3,
                math.ceil(
                    max(0.0, p.billet_min_length_mm - butt_mm)
                    / useful_per_profile_mm
                ),
            )
            max_profiles = math.floor(
                max(0.0, p.billet_max_length_mm - butt_mm)
                / useful_per_profile_mm
            )
            if min_profiles <= max_profiles:
                if best is None or min_profiles < best:
                    best = min_profiles
        return best

    required_profiles = None if selected is not None else _required_unsupported_profiles()
    supported = required_profiles is None
    unsupported_reason = None
    if not supported:
        unsupported_reason = (
            f"More than 2 profiles per billet is not supported by the current PyExtrusion model "
            f"(minimum required: {required_profiles})."
        )
        warnings.append(unsupported_reason)

    viable = selected is not None and supported
    if not viable and supported:
        warnings.append("No supported configuration is viable for this press and process.")
    elif selected is not None and selected.name != "1_billet_1_profile":
        if selected.name == "k_billets_1_profile":
            warnings.append(
                f"Recommended multi-billet configuration: {selected.billets_per_pull} billets per continuous pull."
            )
        else:
            warnings.append("Recommended special configuration: 1_billet_2_profiles.")

    if fixed_by_user:
        if any("table length" in reason or "fits the table" in reason for reason in cfg_one.reasons):
            warnings.insert(0, "User-defined cuts exceed the physical table allowance after saw kerfs.")
        if any("above maximum" in reason for reason in cfg_one.reasons) and any(
            "above maximum" in reason for reason in cfg_double.reasons
        ):
            warnings.insert(0, "User-defined cuts require a billet longer than the press maximum.")
        if not viable and not any("User-defined" in warning for warning in warnings):
            warnings.insert(0, "User-defined cuts do not produce a viable supported configuration.")

    selected_cuts = selected.cuts if selected else max((c.cuts for c in configurations), default=0)
    profiles_per_billet = selected.profiles_per_billet if selected else 0
    billets_per_pull = selected.billets_per_pull if selected else 0
    cuts_per_pull = selected.cuts_per_pull if selected else 0
    bars_per_pull = selected.bars_per_pull if selected else 0
    bars_per_billet = (
        selected_cuts * prof.exits * profiles_per_billet
        if selected and selected_cuts >= 1 else 0
    )

    applied_front_scrap = data.front_scrap_m
    applied_front_scrap_source = "standard"
    if selected and selected.profiles_per_billet == 1 and selected.front_scrap_source == "user_override":
        applied_front_scrap = selected.front_scrap_per_billet_m
        applied_front_scrap_source = "multi_billet_user_override"
        warnings.append(
            "Multi-billet front scrap is applied per billet and its billet geometry is recalculated."
        )
    elif selected and selected.profiles_per_billet == 1 and selected.billets_per_pull >= 2:
        applied_front_scrap = selected.front_scrap_per_billet_m
        applied_front_scrap_source = "multi_billet_standard_fallback"

    if selected and theoretical_cuts:
        cuts_ratio = min(1.0, max(0.0, selected.cuts_per_pull / theoretical_cuts))
    else:
        cuts_ratio = 0.0
    table_ratio = (selected.table_occupancy_length_m / p.table_length_m) if selected else 0.0
    billet_ratio = (selected.billet_length_mm / p.billet_max_length_mm) if selected else 0.0
    geometric_index = 100.0 * (0.40 * table_ratio + 0.30 * billet_ratio + 0.30 * cuts_ratio)
    t_ext_one = (selected.length_per_billet_m / exit_speed_m_min) if viable and selected else 0.0
    recommended_billet_length = math.ceil(selected.billet_length_mm) if selected else 0

    return _ResolvedProcess(
        press=p,
        profile=prof,
        cut_m=cut_m,
        kg_m_total=kg_m_total,
        area_one=area_one,
        area_total=area_total,
        extrusion_ratio_value=re,
        extrusion_ratio_status_value=re_status,
        exit_speed_m_min=exit_speed_m_min,
        ram_speed_m_min=ram_m_min,
        ram_speed_mm_s=ram_mm_s,
        speed_source=speed_source,
        theoretical_cuts=theoretical_cuts,
        warnings=tuple(warnings),
        butt_mm=butt_mm,
        butt_source=butt_source,
        configurations=configurations,
        valid_configurations=valid,
        selected=selected,
        required_profiles_per_billet=required_profiles,
        supported=supported,
        unsupported_reason=unsupported_reason,
        viable=viable,
        selected_cuts=selected_cuts,
        profiles_per_billet=profiles_per_billet,
        billets_per_pull=billets_per_pull,
        cuts_per_pull=cuts_per_pull,
        bars_per_pull=bars_per_pull,
        bars_per_billet=bars_per_billet,
        applied_front_scrap_m=applied_front_scrap,
        applied_front_scrap_source=applied_front_scrap_source,
        multi_scrap_m=multi_scrap,
        multi_scrap_source=multi_scrap_source,
        cuts_source="user_override" if fixed_by_user else "automatic_billet_first",
        table_ratio=table_ratio,
        billet_ratio=billet_ratio,
        cuts_ratio=cuts_ratio,
        geometric_index=geometric_index,
        extrusion_time_per_billet_min=t_ext_one,
        recommended_billet_length_mm=recommended_billet_length,
    )


def calculate_process(data: ProcessInput) -> ProcessResult:
    """Evaluate a quantity-free extrusion process without creating a fictitious order."""
    r = _resolve_process(data)
    selected = r.selected
    result = ProcessResult(
        viable=r.viable,
        supported=r.supported,
        unsupported_reason=r.unsupported_reason,
        required_profiles_per_billet=r.required_profiles_per_billet,
        press_name=r.press.name,
        recommended_configuration=selected.name if selected else None,
        valid_configurations=tuple(cfg.name for cfg in r.valid_configurations),
        configurations=r.configurations,
        profile_section_per_exit_m2=r.area_one,
        profile_section_total_m2=r.area_total,
        extrusion_ratio=r.extrusion_ratio_value,
        extrusion_ratio_status=r.extrusion_ratio_status_value,
        exit_speed_m_min=r.exit_speed_m_min,
        ram_speed_m_min=r.ram_speed_m_min,
        ram_speed_mm_s=r.ram_speed_mm_s,
        speed_input_source=r.speed_source,
        theoretical_cuts=r.theoretical_cuts,
        cuts=r.selected_cuts,
        cuts_per_pull=r.cuts_per_pull,
        billets_per_pull=r.billets_per_pull,
        profiles_per_billet=r.profiles_per_billet,
        bars_per_billet=r.bars_per_billet,
        bars_per_pull=r.bars_per_pull,
        pull_length_m=selected.length_per_billet_m if selected else 0.0,
        profile_pull_length_m=selected.length_per_profile_m if selected else 0.0,
        extruded_length_per_billet_m=selected.length_per_billet_m if selected else 0.0,
        table_occupancy_length_m=selected.table_occupancy_length_m if selected else 0.0,
        configuration_total_length_m=selected.total_configuration_length_m if selected else 0.0,
        table_ratio=r.table_ratio,
        billet_ratio=r.billet_ratio,
        cuts_ratio=r.cuts_ratio,
        geometric_index=r.geometric_index,
        butt_mm=r.butt_mm,
        butt_source=r.butt_source,
        billet_useful_length_mm=selected.billet_useful_length_mm if selected else 0.0,
        billet_length_mm=selected.billet_length_mm if selected else 0.0,
        recommended_billet_length_mm=r.recommended_billet_length_mm,
        billet_kg_per_mm=r.press.billet_weight_kg_per_mm,
        applied_front_scrap_m=r.applied_front_scrap_m,
        applied_front_scrap_source=r.applied_front_scrap_source,
        cuts_source=r.cuts_source,
        extrusion_time_per_billet_min=r.extrusion_time_per_billet_min,
        dead_time_sec=r.press.dead_time_sec,
        warnings=r.warnings,
    )
    _assert_finite_result(result)
    return result


def calculate(data: StudyInput) -> CalculationResult:
    """Calculate the PyExtrusion direct-extrusion productivity model.

    The v2.8 calculation preserves billet-first configuration selection while
    reserving physical puller/final-saw kerf length in billet geometry and
    technical extrusion time. Startup and complexity remain modeled planning
    allowances rather than physical material added to the billet.
    """
    _validate(data)
    r = _resolve_process(data)
    p, prof = r.press, r.profile
    cut_m = r.cut_m
    kg_m_total = r.kg_m_total
    area_one, area_total = r.area_one, r.area_total
    re, re_status = r.extrusion_ratio_value, r.extrusion_ratio_status_value
    exit_speed_m_min = r.exit_speed_m_min
    ram_m_min, ram_mm_s = r.ram_speed_m_min, r.ram_speed_mm_s
    speed_source = r.speed_source
    theoretical_cuts = r.theoretical_cuts
    warnings = list(r.warnings)
    butt_mm, butt_source = r.butt_mm, r.butt_source
    configurations, valid = r.configurations, r.valid_configurations
    selected = r.selected
    required_profiles = r.required_profiles_per_billet
    supported, unsupported_reason, viable = r.supported, r.unsupported_reason, r.viable
    selected_cuts = r.selected_cuts
    fully_nonviable_zero_cuts = (not viable and selected_cuts == 0)
    profiles_per_billet = r.profiles_per_billet
    billets_per_pull = r.billets_per_pull
    cuts_per_pull = r.cuts_per_pull
    bars_per_pull = r.bars_per_pull
    bars_per_billet = r.bars_per_billet
    multi_scrap, multi_scrap_source = r.multi_scrap_m, r.multi_scrap_source
    selected_front_scrap = r.applied_front_scrap_m
    selected_front_scrap_source = r.applied_front_scrap_source
    cuts_source = r.cuts_source

    supplement_factor = 1.10 if data.supplement_10_pct else 1.00
    if data.effective_bars_target_override is not None:
        bars_target_effective = data.effective_bars_target_override
    else:
        bars_target_effective = (
            math.ceil(data.bars_requested * supplement_factor)
            if data.supplement_10_pct else data.bars_requested
        )
    billets = math.ceil(bars_target_effective / bars_per_billet) if bars_per_billet else 0
    bars_manufactured = billets * bars_per_billet
    extra_bars = bars_manufactured - bars_target_effective
    extra_pct = (extra_bars / bars_target_effective) * 100.0 if bars_target_effective else 0.0

    if selected and selected.profiles_per_billet == 1:
        k = selected.billets_per_pull
        full_pulls = billets // k if k else 0
        remaining_billets = billets % k if k else 0
        n_pulls = full_pulls + (1 if remaining_billets > 0 else 0)
    elif selected and selected.profiles_per_billet == 2:
        full_pulls = 2 * billets
        remaining_billets = 0
        n_pulls = full_pulls
    else:
        full_pulls = 0
        remaining_billets = 0
        n_pulls = 0

    good_req = data.bars_requested * cut_m * prof.linear_weight_kg_m
    good_effective = bars_target_effective * cut_m * prof.linear_weight_kg_m
    good_made = bars_manufactured * cut_m * prof.linear_weight_kg_m

    kg_start = (5.0 if prof.exits == 1 else 5.0 + 5.0 * prof.exits) * kg_m_total
    kg_complexity = COMPLEXITY_PCT[data.complexity] * good_made
    kg_butt = billets * butt_mm * p.billet_weight_kg_per_mm
    kg_front = selected_front_scrap * kg_m_total * billets * profiles_per_billet
    swarf_billet = billets * p.saws.billet_mm * p.billet_weight_kg_per_mm
    swarf_puller = (p.saws.puller_mm / 1000.0) * kg_m_total * n_pulls

    final_cuts_total = 0
    if selected and selected.profiles_per_billet == 1 and selected_cuts >= 1:
        k = selected.billets_per_pull
        final_cuts_total = full_pulls * (selected_cuts * k + 1)
        if remaining_billets > 0:
            final_cuts_total += selected_cuts * remaining_billets + 1
    elif selected and selected.profiles_per_billet == 2 and selected_cuts >= 1:
        final_cuts_total = 2 * billets * (selected_cuts + 1)
    swarf_final = (p.saws.final_mm / 1000.0) * kg_m_total * final_cuts_total

    fixed_scrap = kg_butt + kg_front + swarf_billet + swarf_puller + swarf_final
    global_scrap = fixed_scrap + kg_start + kg_complexity
    fixed_pct = fixed_scrap / good_made * 100.0 if good_made else 0.0
    global_pct = global_scrap / good_made * 100.0 if good_made else 0.0

    nominal_gross = kg_m_total * exit_speed_m_min * 60.0
    selected_length_m = selected.length_per_billet_m if selected else 0.0

    puller_kerf_m = p.saws.puller_mm / 1000.0
    final_kerf_m = p.saws.final_mm / 1000.0
    base_extruded_length_m = (
        billets
        * profiles_per_billet
        * (selected_cuts * cut_m + selected_front_scrap)
        if selected else 0.0
    )
    exact_extruded_length_m = (
        base_extruded_length_m
        + n_pulls * puller_kerf_m
        + final_cuts_total * final_kerf_m
    )
    t_ext_total = exact_extruded_length_m / exit_speed_m_min if viable else 0.0
    t_ext_one = t_ext_total / billets if billets else r.extrusion_time_per_billet_min

    if (
        selected
        and selected.profiles_per_billet == 1
        and selected.billets_per_pull > 1
        and remaining_billets > 0
        and (puller_kerf_m > 0 or final_kerf_m > 0)
    ):
        warnings.append(
            "Final partial multi-billet pull uses exact order-level saw-kerf accounting; "
            "the process-level billet recommendation represents a complete pull, so the "
            "last partial pull may require plant-specific billet-length adjustment."
        )

    dead_events = max(billets - 1, 0)
    if selected and selected.profiles_per_billet == 2:
        dead_events += billets
    t_dead = dead_events * p.dead_time_sec / 60.0
    t_total = t_ext_total + t_dead
    hours = t_total / 60.0
    cycle = t_total / billets if billets else 0.0

    physical_extruded_losses = kg_front + swarf_puller + swarf_final
    kg_extruded_total = good_made + physical_extruded_losses
    real_gross = kg_extruded_total / hours if hours else 0.0
    real_net = good_made / hours if hours else 0.0

    cuts_ratio = r.cuts_ratio
    table_ratio = r.table_ratio
    billet_ratio = r.billet_ratio
    geometric_index = r.geometric_index

    target = p.target_net_productivity_kg_h
    target_source = p.target_productivity_source
    ratio: float | None = None
    delta_kg_h: float | None = None
    deficit_pct: float | None = None
    relative_score: float | None = None
    fixed_score: float | None = None
    penalty: float | None = None
    productivity_index: float | None = None
    productivity_rating: str | None = None

    if viable:
        fixed_score = _fixed_scrap_score(fixed_pct)
        if target is not None and target > 0:
            ratio = real_net / target
            delta_kg_h = real_net - target
            deficit_pct = max(0.0, (1.0 - ratio) * 100.0)
            relative_score = min(100.0, ratio * 100.0)
            penalty = _productivity_penalty(deficit_pct)
            base_index = (
                0.60 * relative_score
                + 0.20 * fixed_score
                + 0.10 * (cuts_ratio * 100.0)
                + 0.05 * (table_ratio * 100.0)
                + 0.05 * (billet_ratio * 100.0)
            )
            productivity_index = max(0.0, min(100.0, base_index - penalty))
            productivity_rating = _productivity_rating(productivity_index)

    if viable and not fully_nonviable_zero_cuts:
        if cuts_ratio < 0.40:
            warnings.append(
                "Cuts ratio is very low (< 0.40); strong geometric penalty indicated by the model."
            )
        elif cuts_ratio < 0.55:
            warnings.append(
                "Cuts ratio is low (0.40-0.55); medium geometric penalty indicated by the model."
            )
        if fixed_pct > 12.0:
            warnings.append("Fixed scrap exceeds 12%; strong industrial penalty indicated by the model.")
        if bars_per_billet <= 3:
            warnings.append("Bars per billet are <= 3; additional industrial penalty is indicated by the model.")
        if deficit_pct is not None and deficit_pct > 5.0:
            warnings.append(f"Net productivity is {deficit_pct:.1f}% below the press reference target.")

    recommended_billet_length = math.ceil(selected.billet_length_mm) if selected else 0

    status_block = StatusResult(
        viable=viable,
        supported=supported,
        unsupported_reason=unsupported_reason,
        required_profiles_per_billet=required_profiles,
        recommended_configuration=selected.name if selected else None,
    )

    geometry_block = GeometryResult(
        profile_section_per_exit_m2=area_one,
        profile_section_total_m2=area_total,
        container_area_m2=p.container_area_m2,
        billet_area_m2=p.billet_area_m2,
        extrusion_ratio=re,
        extrusion_ratio_status=re_status,
        exit_speed_m_min=exit_speed_m_min,
        ram_speed_m_min=ram_m_min,
        ram_speed_mm_s=ram_mm_s,
        theoretical_cuts=theoretical_cuts,
        cuts=selected_cuts,
        cuts_per_pull=cuts_per_pull,
        billets_per_pull=billets_per_pull,
        profiles_per_billet=profiles_per_billet,
        pull_length_m=selected_length_m,
        profile_pull_length_m=selected.length_per_profile_m if selected else 0.0,
        extruded_length_per_billet_m=selected.length_per_billet_m if selected else 0.0,
        table_occupancy_length_m=selected.table_occupancy_length_m if selected else 0.0,
        configuration_total_length_m=selected.total_configuration_length_m if selected else 0.0,
        table_ratio=table_ratio,
        billet_ratio=billet_ratio,
        cuts_ratio=cuts_ratio,
        geometric_index=geometric_index,
    )
    billet_block = BilletResult(
        useful_length_mm=selected.billet_useful_length_mm if selected else 0.0,
        length_mm=selected.billet_length_mm if selected else 0.0,
        recommended_length_mm=recommended_billet_length,
        count=billets,
        butt_mm=butt_mm,
        butt_source=butt_source,
        kg_per_mm=p.billet_weight_kg_per_mm,
    )
    production_block = ProductionResult(
        profiles_per_billet=profiles_per_billet,
        billets_per_pull=billets_per_pull,
        cuts_per_pull=cuts_per_pull,
        bars_per_pull=bars_per_pull,
        bars_per_billet=bars_per_billet,
        billets=billets,
        full_pulls=full_pulls,
        remaining_billets=remaining_billets,
        n_pulls=n_pulls,
        bars_requested=data.bars_requested,
        bars_target_effective=bars_target_effective,
        supplement_10_pct=data.supplement_10_pct,
        supplement_factor=supplement_factor,
        bars_manufactured=bars_manufactured,
        extra_bars=extra_bars,
        extra_pct=extra_pct,
        good_kg_requested=good_req,
        good_kg_effective_target=good_effective,
        good_kg_manufactured=good_made,
    )
    scrap_block = ScrapResult(
        start_kg=kg_start,
        complexity_kg=kg_complexity,
        butt_kg=kg_butt,
        front_scrap_kg=kg_front,
        billet_saw_kg=swarf_billet,
        puller_saw_kg=swarf_puller,
        final_saw_kg=swarf_final,
        fixed_kg=fixed_scrap,
        fixed_pct=fixed_pct,
        total_kg=global_scrap,
        total_pct=global_pct,
        extruded_losses_kg=physical_extruded_losses,
    )
    productivity_block = ProductivityResult(
        nominal_gross_kg_h=nominal_gross,
        real_gross_kg_h=real_gross,
        real_net_kg_h=real_net,
        extruded_total_kg=kg_extruded_total,
        target_net_kg_h=target,
        target_source=target_source,
        ratio=ratio,
        delta_kg_h=delta_kg_h,
        deficit_pct=deficit_pct,
        relative_score=relative_score,
        fixed_scrap_score=fixed_score,
        penalty_points=penalty,
        productivity_index=productivity_index,
        productivity_index_rating=productivity_rating,
    )
    timing_block = TimingResult(
        extrusion_per_billet_min=t_ext_one,
        extrusion_total_min=t_ext_total,
        dead_time_events=dead_events,
        dead_time_total_min=t_dead,
        total_min=t_total,
        cycle_per_billet_min=cycle,
        total_hours=hours,
    )
    process_block = ProcessTraceResult(
        butt_source=butt_source,
        standard_front_scrap_m=data.front_scrap_m,
        multi_billet_front_scrap_m=multi_scrap,
        multi_billet_front_scrap_source=multi_scrap_source,
        applied_front_scrap_m=selected_front_scrap,
        applied_front_scrap_source=selected_front_scrap_source,
        cuts_source=cuts_source,
        speed_input_source=speed_source,
        supplement_10_pct=data.supplement_10_pct,
        supplement_factor=supplement_factor,
        target_productivity_source=target_source,
    )

    valid_names = tuple(dict.fromkeys(cfg.name for cfg in valid))
    result = CalculationResult(
        viable=viable,
        supported=supported,
        unsupported_reason=unsupported_reason,
        required_profiles_per_billet=required_profiles,
        press_name=p.name,
        recommended_configuration=selected.name if selected else None,
        valid_configurations=valid_names,
        configurations=configurations,
        profile_section_per_exit_m2=area_one,
        profile_section_total_m2=area_total,
        extrusion_ratio=re,
        extrusion_ratio_status=re_status,
        exit_speed_m_min=exit_speed_m_min,
        ram_speed_m_min=ram_m_min,
        ram_speed_mm_s=ram_mm_s,
        theoretical_cuts=theoretical_cuts,
        cuts=selected_cuts,
        cuts_per_pull=cuts_per_pull,
        billets_per_pull=billets_per_pull,
        profiles_per_billet=profiles_per_billet,
        n_pulls=n_pulls,
        full_pulls=full_pulls,
        remaining_billets=remaining_billets,
        bars_per_pull=bars_per_pull,
        pull_length_m=selected_length_m,
        profile_pull_length_m=selected.length_per_profile_m if selected else 0.0,
        extruded_length_per_billet_m=selected.length_per_billet_m if selected else 0.0,
        table_occupancy_length_m=selected.table_occupancy_length_m if selected else 0.0,
        configuration_total_length_m=selected.total_configuration_length_m if selected else 0.0,
        butt_mm=butt_mm,
        billet_useful_length_mm=selected.billet_useful_length_mm if selected else 0.0,
        billet_length_mm=selected.billet_length_mm if selected else 0.0,
        recommended_billet_length_mm=recommended_billet_length,
        bars_per_billet=bars_per_billet,
        billets=billets,
        bars_target_effective=bars_target_effective,
        supplement_10_pct=data.supplement_10_pct,
        bars_manufactured=bars_manufactured,
        extra_bars=extra_bars,
        extra_pct=extra_pct,
        good_kg_requested=good_req,
        good_kg_effective_target=good_effective,
        good_kg_manufactured=good_made,
        fixed_scrap_kg=fixed_scrap,
        fixed_scrap_pct=fixed_pct,
        global_scrap_kg=global_scrap,
        global_scrap_pct=global_pct,
        nominal_gross_kg_h=nominal_gross,
        real_gross_kg_h=real_gross,
        real_net_kg_h=real_net,
        target_net_productivity_kg_h=target,
        productivity_ratio=ratio,
        productivity_deficit_pct=deficit_pct,
        productivity_index=productivity_index,
        extrusion_time_per_billet_min=t_ext_one,
        extrusion_time_total_min=t_ext_total,
        dead_time_events=dead_events,
        dead_time_total_min=t_dead,
        total_time_min=t_total,
        cycle_time_per_billet_min=cycle,
        table_ratio=table_ratio,
        billet_ratio=billet_ratio,
        cuts_ratio=cuts_ratio,
        geometric_index=geometric_index,
        status=status_block,
        geometry=geometry_block,
        billet=billet_block,
        production=production_block,
        scrap=scrap_block,
        productivity=productivity_block,
        timing=timing_block,
        process=process_block,
        warnings=tuple(warnings),
    )
    _assert_finite_result(result)
    return result
