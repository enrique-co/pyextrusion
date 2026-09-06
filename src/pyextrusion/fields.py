from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import UnknownResultFieldError, UnknownResultSectionError


@dataclass(frozen=True)
class FieldInfo:
    path: str
    section: str
    unit: str
    data_type: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _f(path: str, unit: str, data_type: str, description: str) -> FieldInfo:
    return FieldInfo(path, path.split(".", 1)[0], unit, data_type, description)


_FIELD_LIST = (
    _f("status.viable", "bool", "bool", "Whether a supported configuration is physically viable for the press and process."),
    _f("status.supported", "bool", "bool", "Whether the scenario is covered by the current PyExtrusion calculation model."),
    _f("status.unsupported_reason", "text", "str|null", "Controlled explanation when the scenario is outside the supported model."),
    _f("status.required_profiles_per_billet", "profiles/billet", "int|null", "Minimum profiles per billet detected when the case would require more than the supported maximum of two."),
    _f("status.recommended_configuration", "text", "str|null", "Recommended supported configuration family after billet-first optimisation."),

    _f("geometry.profile_section_per_exit_m2", "m²", "float", "Cross-sectional area of one profile exit."),
    _f("geometry.profile_section_total_m2", "m²", "float", "Total profile cross-sectional area across all exits."),
    _f("geometry.container_area_m2", "m²", "float", "Internal container-bore area used for extrusion ratio and ram-speed calculations."),
    _f("geometry.billet_area_m2", "m²", "float", "Actual billet area used for billet mass and kg/mm calculations."),
    _f("geometry.extrusion_ratio", "ratio", "float", "Container-bore area divided by total extruded profile area."),
    _f("geometry.extrusion_ratio_status", "text", "str", "Informative RE classification: low, ok or high; thresholds depend on solid/plate versus hollow/tubular."),
    _f("geometry.exit_speed_m_min", "m/min", "float", "Resolved profile exit speed used by the calculation, either supplied directly or derived from ram speed."),
    _f("geometry.ram_speed_m_min", "m/min", "float", "Ram speed from volume constancy using container-bore area."),
    _f("geometry.ram_speed_mm_s", "mm/s", "float", "Ram speed expressed in millimetres per second."),
    _f("geometry.theoretical_cuts", "count", "int", "Maximum theoretical cuts from table length before billet-limit optimisation."),
    _f("geometry.cuts", "count", "int", "Cuts per billet selected by billet-first optimisation or supplied manually."),
    _f("geometry.cuts_per_pull", "count", "int", "Finished cut positions represented by the full pull geometry; for multi-billet this is cuts per billet × billets per pull."),
    _f("geometry.billets_per_pull", "billets/pull", "int", "Billets combined into one continuous pull after billet-first optimisation."),
    _f("geometry.profiles_per_billet", "profiles/billet", "int", "Sequential profiles produced by one billet; supported values are 1 or 2."),
    _f("geometry.pull_length_m", "m", "float", "Total length extruded by one billet; retained as a flat compatibility field."),
    _f("geometry.profile_pull_length_m", "m", "float", "Length of one complete pull/profile including applied front scrap."),
    _f("geometry.extruded_length_per_billet_m", "m/billet", "float", "Total length extruded by one billet across sequential pulls."),
    _f("geometry.table_occupancy_length_m", "m", "float", "Runout-table length occupied by the recommended configuration."),
    _f("geometry.configuration_total_length_m", "m", "float", "Total length represented by the recommended special configuration."),
    _f("geometry.table_ratio", "ratio", "float", "Table occupancy divided by available table length."),
    _f("geometry.billet_ratio", "ratio", "float", "Evaluated billet length divided by maximum billet length."),
    _f("geometry.cuts_ratio", "ratio", "float", "Cuts represented by the full table-occupying pull divided by theoretical table cuts."),
    _f("geometry.geometric_index", "score", "float", "Geometric/industrial fit index on the documented 0-100 scale."),

    _f("billet.useful_length_mm", "mm", "float", "Useful billet length converted into extruded profile before butt discard."),
    _f("billet.length_mm", "mm", "float", "Mathematical total billet length used for the recommended configuration."),
    _f("billet.recommended_length_mm", "mm", "int", "Industrial suggestion obtained by rounding the mathematical billet length upward to the next whole millimetre."),
    _f("billet.count", "count", "int", "Number of billets required for the production quantity."),
    _f("billet.butt_mm", "mm", "float", "Butt-discard length applied to the calculation."),
    _f("billet.butt_source", "text", "str", "Origin of butt value: default_rule or user_override."),
    _f("billet.kg_per_mm", "kg/mm", "float", "Billet mass coefficient derived from actual billet geometry/density or supplied override."),

    _f("production.profiles_per_billet", "profiles/billet", "int", "Complete sequential pulls produced by one billet; maximum supported value is 2."),
    _f("production.billets_per_pull", "billets/pull", "int", "Number of billets grouped into one continuous pull; dynamically limited by billet and table geometry."),
    _f("production.cuts_per_pull", "count", "int", "Cuts represented by a complete pull."),
    _f("production.bars_per_pull", "bars/pull", "int", "Finished bars represented by a complete pull."),
    _f("production.bars_per_billet", "bars/billet", "int", "Bars contributed by one billet: cuts × exits × profiles_per_billet."),
    _f("production.billets", "count", "int", "Number of billets required after ceiling to whole billets."),
    _f("production.full_pulls", "count", "int", "Number of complete pulls in the production order."),
    _f("production.remaining_billets", "billets", "int", "Billets in the final partial multi-billet pull, if any."),
    _f("production.n_pulls", "count", "int", "Total number of pulls, including a final partial pull when present."),
    _f("production.bars_requested", "bars", "int", "Base bars requested before optional 10% demand supplement."),
    _f("production.bars_target_effective", "bars", "int", "Effective whole-bar target after optional 10% supplement."),
    _f("production.supplement_10_pct", "bool", "bool", "Whether the explicit optional 10% demand supplement was enabled."),
    _f("production.supplement_factor", "factor", "float", "Demand multiplier: 1.10 when supplement is enabled, otherwise 1.00."),
    _f("production.bars_manufactured", "bars", "int", "Bars manufactured after rounding to complete billets."),
    _f("production.extra_bars", "bars", "int", "Bars above effective target caused only by complete-billet rounding."),
    _f("production.extra_pct", "%", "float", "Extra bars caused only by complete-billet rounding; independent from the optional 10% supplement."),
    _f("production.good_kg_requested", "kg", "float", "Good product mass corresponding to base requested bars."),
    _f("production.good_kg_effective_target", "kg", "float", "Good product mass corresponding to effective bar target."),
    _f("production.good_kg_manufactured", "kg", "float", "Good product mass corresponding to manufactured bars."),

    _f("scrap.start_kg", "kg", "float", "Start-up scrap from the documented PyExtrusion startup-length rule."),
    _f("scrap.complexity_kg", "kg", "float", "Complexity allowance mass: normal 3%, medium 5%, high 7%."),
    _f("scrap.butt_kg", "kg", "float", "Scrap mass corresponding to billet butt discard."),
    _f("scrap.front_scrap_kg", "kg", "float", "Scrap mass corresponding to applied front scrap."),
    _f("scrap.billet_saw_kg", "kg", "float", "Billet-saw kerf loss; zero when billet kerf is 0 mm."),
    _f("scrap.puller_saw_kg", "kg", "float", "Puller-saw kerf loss; zero when puller kerf is 0 mm."),
    _f("scrap.final_saw_kg", "kg", "float", "Final-saw kerf loss; zero when final kerf is 0 mm."),
    _f("scrap.fixed_kg", "kg", "float", "Total fixed process losses: butt, front scrap and saw losses."),
    _f("scrap.fixed_pct", "%", "float", "Fixed process losses divided by manufactured good kilograms."),
    _f("scrap.total_kg", "kg", "float", "Total losses including fixed, startup and complexity losses."),
    _f("scrap.total_pct", "%", "float", "Total losses divided by manufactured good kilograms."),
    _f("scrap.extruded_losses_kg", "kg", "float", "Losses counted as material that passed through the die for real productivity."),

    _f("productivity.nominal_gross_kg_h", "kg/h", "float", "Nominal gross output from total linear weight × exit speed × 60."),
    _f("productivity.real_gross_kg_h", "kg/h", "float", "Real gross extruded output divided by total elapsed hours."),
    _f("productivity.real_net_kg_h", "kg/h", "float", "Manufactured good kilograms divided by total elapsed hours."),
    _f("productivity.extruded_total_kg", "kg", "float", "Manufactured good mass plus losses that passed through the die."),
    _f("productivity.target_net_kg_h", "kg/h", "float|null", "Press reference net productivity supplied by the user or inferred by the PyExtrusion nominal-size heuristic."),
    _f("productivity.target_source", "text", "str", "Origin of target productivity: user_value, inferred_from_nominal_size, or unavailable."),
    _f("productivity.ratio", "ratio", "float|null", "Real net productivity divided by press reference target."),
    _f("productivity.delta_kg_h", "kg/h", "float|null", "Informative real-net minus target productivity delta."),
    _f("productivity.deficit_pct", "%", "float|null", "Relative productivity deficit: max(0, (1-ratio)×100)."),
    _f("productivity.relative_score", "score", "float|null", "Relative productivity score capped at 100."),
    _f("productivity.fixed_scrap_score", "score", "float|null", "Fixed-scrap score used internally by the productivity index."),
    _f("productivity.penalty_points", "points", "float|null", "Percentage-based infraproductivity penalty used by the productivity index."),
    _f("productivity.productivity_index", "score", "float|null", "0-100 orientative industrial-capacity utilisation index; not a definitive decision criterion."),
    _f("productivity.productivity_index_rating", "text", "str|null", "Orientative rating: very_favorable, favorable, acceptable, unfavorable, or highly_penalized."),

    _f("timing.extrusion_per_billet_min", "min", "float", "Extrusion time for one billet from actual extruded length and exit speed."),
    _f("timing.extrusion_total_min", "min", "float", "Total extrusion time for all billets."),
    _f("timing.dead_time_events", "count", "int", "Number of technical dead-time events used by the selected configuration."),
    _f("timing.dead_time_total_min", "min", "float", "Total technical dead time."),
    _f("timing.total_min", "min", "float", "Total production time: extrusion plus technical dead time."),
    _f("timing.cycle_per_billet_min", "min/billet", "float", "Average total cycle time per billet."),
    _f("timing.total_hours", "h", "float", "Total production time expressed in hours."),

    _f("process.butt_source", "text", "str", "Trace value describing the source of the butt length."),
    _f("process.standard_front_scrap_m", "m", "float", "Standard front-scrap input supplied for the study."),
    _f("process.multi_billet_front_scrap_m", "m/billet", "float", "Front-scrap value available for multi-billet configurations."),
    _f("process.multi_billet_front_scrap_source", "text", "str", "Origin of the multi-billet front-scrap value."),
    _f("process.applied_front_scrap_m", "m/billet", "float", "Front-scrap value actually used by the recommended configuration."),
    _f("process.applied_front_scrap_source", "text", "str", "Origin of the front-scrap value actually used."),
    _f("process.cuts_source", "text", "str", "Whether cuts were selected automatically or supplied by the user."),
    _f("process.speed_input_source", "text", "str", "Speed input used to resolve the process: exit_speed_user_value or ram_speed_user_value."),
    _f("process.supplement_10_pct", "bool", "bool", "Whether the explicit 10% demand supplement was enabled."),
    _f("process.supplement_factor", "factor", "float", "Demand multiplier applied by the supplement rule."),
    _f("process.target_productivity_source", "text", "str", "Trace source for the press productivity target."),
)

FIELD_GLOSSARY: dict[str, FieldInfo] = {item.path: item for item in _FIELD_LIST}
RESULT_SECTIONS = ("status", "geometry", "billet", "production", "scrap", "productivity", "timing", "process")


def list_fields(section: str | None = None) -> tuple[FieldInfo, ...]:
    if section is not None and section not in RESULT_SECTIONS:
        raise UnknownResultSectionError(f"Unknown result section: {section}")
    return tuple(item for item in _FIELD_LIST if section is None or item.section == section)


def describe_field(path: str) -> FieldInfo:
    try:
        return FIELD_GLOSSARY[path]
    except KeyError as exc:
        raise UnknownResultFieldError(f"Unknown result field: {path}") from exc
