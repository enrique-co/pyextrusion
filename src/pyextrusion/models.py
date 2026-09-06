from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields as dataclass_fields, is_dataclass, replace as dataclass_replace
from typing import Any, Literal

from .errors import (
    InvalidPressConfigurationError,
    InvalidProfileInputError,
    InvalidProductionInputError,
    InvalidResultSelectionError,
    InvalidStudyAdjustmentError,
    UnknownResultFieldError,
    UnknownResultSectionError,
)
from .fields import RESULT_SECTIONS, list_fields
from ._strict import require_bool, require_int, require_kerf, require_number, require_string

ProfileType = Literal["solid", "plate", "hollow", "tubular"]
CanonicalProfileType = Literal["solid", "hollow"]

PROFILE_TYPE_ALIASES: dict[str, CanonicalProfileType] = {
    "solid": "solid",
    "plate": "solid",
    "hollow": "hollow",
    "tubular": "hollow",
}
PROFILE_TYPE_VALID_VALUES = tuple(PROFILE_TYPE_ALIASES)


def normalize_profile_type(value: str | None) -> CanonicalProfileType:
    """Validate and normalize public profile-type aliases to engine values."""
    if value is None or not str(value).strip():
        raise InvalidProfileInputError(
            "profile.profile_type is required. Valid values: solid, plate, hollow, tubular"
        )
    normalized = str(value).strip().lower()
    try:
        return PROFILE_TYPE_ALIASES[normalized]
    except KeyError as exc:
        raise InvalidProfileInputError(
            f"Invalid profile.profile_type={value!r}. Valid values: solid, plate, hollow, tubular"
        ) from exc


Complexity = Literal["normal", "medium", "high"]
ConfigurationName = Literal[
    "1_billet_1_profile",
    "k_billets_1_profile",
    "1_billet_2_profiles",
]

DEFAULT_CONTAINER_DIAMETER_FACTOR = 1.035
DEFAULT_DEAD_TIME_SEC = 15.0
DEFAULT_DENSITY_KG_M3 = 2700.0
DEFAULT_BUTT_MM = {"solid": 15.0, "hollow": 20.0}


def default_billet_limits(nominal_size_in: float | None) -> tuple[float, float] | None:
    """Return PyExtrusion v2.4 billet-length defaults for nominal sizes 6-16 in."""
    if nominal_size_in is None:
        return None
    size = int(round(float(nominal_size_in)))
    if size == 6:
        return 300.0, 800.0
    if size == 7:
        return 400.0, 900.0
    if size == 8:
        return 450.0, 1200.0
    if size == 9:
        return 500.0, 1300.0
    if size == 10:
        return 550.0, 1400.0
    if 11 <= size <= 16:
        return 600.0, 1500.0
    return None


def default_target_productivity_kg_h(nominal_size_in: float | None) -> float | None:
    """PyExtrusion heuristic target productivity for nominal sizes 6-16 in."""
    if nominal_size_in is None or not 6.0 <= float(nominal_size_in) <= 16.0:
        return None
    return 1600.0 + (float(nominal_size_in) - 8.0) * 600.0


class _ResultBlock:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SawSpec:
    """Saw kerfs in millimetres. Valid values are 0 or 3-10 mm."""

    billet_mm: float = 5.0
    puller_mm: float = 5.0
    final_mm: float = 5.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "billet_mm", require_kerf(self.billet_mm, "press.saws.billet_mm", InvalidPressConfigurationError))
        object.__setattr__(self, "puller_mm", require_kerf(self.puller_mm, "press.saws.puller_mm", InvalidPressConfigurationError))
        object.__setattr__(self, "final_mm", require_kerf(self.final_mm, "press.saws.final_mm", InvalidPressConfigurationError))


@dataclass(frozen=True)
class ButtRule:
    """Legacy/custom plant rule for butt-discard length.

    PyExtrusion v2.4 no longer requires butt rules: when none are supplied,
    the default is 15 mm for solid/plate and 20 mm for hollow/tubular.
    Existing custom rules remain supported for backwards compatibility.

    Bounds follow the historical convention:
    - lower bound is exclusive
    - upper bound is inclusive
    """

    profile_type: ProfileType
    max_total_linear_weight_kg_m: float | None
    butt_mm: float
    min_total_linear_weight_kg_m: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_type", normalize_profile_type(self.profile_type))
        object.__setattr__(self, "butt_mm", require_number(self.butt_mm, "press.butt_rules.butt_mm", InvalidPressConfigurationError, minimum=0.0))
        if self.min_total_linear_weight_kg_m is not None:
            object.__setattr__(self, "min_total_linear_weight_kg_m", require_number(self.min_total_linear_weight_kg_m, "press.butt_rules.min_total_linear_weight_kg_m", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True))
        if self.max_total_linear_weight_kg_m is not None:
            object.__setattr__(self, "max_total_linear_weight_kg_m", require_number(self.max_total_linear_weight_kg_m, "press.butt_rules.max_total_linear_weight_kg_m", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True))

    def matches(self, profile_type: ProfileType, kg_m_total: float) -> bool:
        if self.profile_type != profile_type:
            return False
        if self.min_total_linear_weight_kg_m is not None and kg_m_total <= self.min_total_linear_weight_kg_m:
            return False
        if self.max_total_linear_weight_kg_m is not None and kg_m_total > self.max_total_linear_weight_kg_m:
            return False
        return True


@dataclass(frozen=True, init=False)
class PressSpec:
    """Technical configuration for one direct aluminium extrusion press.

    ``table_length_m`` is mandatory. Other geometry can be supplied directly
    or inferred from ``nominal_size_in`` using the documented PyExtrusion v2.4
    defaults.

    The constructor accepts historical v0.x names (``nominal_force_t``,
    ``billet_min_mm``...) as compatibility aliases. New code should prefer the
    v2.0 names exposed as dataclass attributes.
    """

    name: str
    table_length_m: float
    nominal_size_in: int | None
    billet_diameter_mm: float
    container_diameter_mm: float
    billet_min_length_mm: float
    billet_max_length_mm: float
    dead_time_sec: float
    density_kg_m3: float
    saws: SawSpec
    target_net_productivity_kg_h: float | None
    press_force_t: float | None
    billet_area_m2_override: float | None = field(compare=False)
    billet_kg_per_mm_override: float | None
    butt_rules: tuple[ButtRule, ...]

    _nominal_size_source: str = field(init=False, repr=False, compare=False)
    _billet_diameter_source: str = field(init=False, repr=False, compare=False)
    _container_diameter_source: str = field(init=False, repr=False, compare=False)
    _billet_limits_source: str = field(init=False, repr=False, compare=False)
    _target_productivity_source: str = field(init=False, repr=False, compare=False)

    def __init__(
        self,
        name: str,
        nominal_force_t: float | None = None,
        container_diameter_mm: float | None = None,
        billet_diameter_mm: float | None = None,
        billet_min_mm: float | None = None,
        billet_max_mm: float | None = None,
        table_length_m: float | None = None,
        dead_time_sec: float = DEFAULT_DEAD_TIME_SEC,
        aluminium_density_kg_m3: float = DEFAULT_DENSITY_KG_M3,
        billet_area_m2_override: float | None = None,
        billet_weight_kg_per_mm_override: float | None = None,
        saws: SawSpec | None = None,
        butt_rules: tuple[ButtRule, ...] = (),
        target_net_productivity_kg_h: float | None = None,
        recommended_min_linear_weight_kg_m: float | None = None,
        *,
        nominal_size_in: int | None = None,
        press_force_t: float | None = None,
        billet_min_length_mm: float | None = None,
        billet_max_length_mm: float | None = None,
        density_kg_m3: float | None = None,
        billet_kg_per_mm_override: float | None = None,
    ) -> None:
        del recommended_min_linear_weight_kg_m  # removed from v2.0; accepted only for compatibility

        require_string(name, "press.name", InvalidPressConfigurationError)
        table = require_number(table_length_m, "press.table_length_m", InvalidPressConfigurationError, minimum=10.0, maximum=100.0)
        dead_time = require_number(dead_time_sec, "press.dead_time_sec", InvalidPressConfigurationError, minimum=5.0, maximum=30.0)

        if press_force_t is not None and nominal_force_t is not None:
            pf = require_number(press_force_t, "press.press_force_t", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            nf = require_number(nominal_force_t, "press.nominal_force_t", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            if pf != nf:
                raise InvalidPressConfigurationError("press_force_t and legacy nominal_force_t disagree; provide only one value")
        resolved_force = press_force_t if press_force_t is not None else nominal_force_t
        if resolved_force is not None:
            resolved_force = require_number(resolved_force, "press.press_force_t", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)

        if density_kg_m3 is not None and aluminium_density_kg_m3 != DEFAULT_DENSITY_KG_M3:
            d_new = require_number(density_kg_m3, "press.density_kg_m3", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            d_old = require_number(aluminium_density_kg_m3, "press.aluminium_density_kg_m3", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            if d_new != d_old:
                raise InvalidPressConfigurationError("density_kg_m3 and legacy aluminium_density_kg_m3 disagree; provide only one value")
        resolved_density = density_kg_m3 if density_kg_m3 is not None else aluminium_density_kg_m3
        resolved_density = require_number(resolved_density, "press.density_kg_m3", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)

        if billet_kg_per_mm_override is not None and billet_weight_kg_per_mm_override is not None:
            b_new = require_number(billet_kg_per_mm_override, "press.billet_kg_per_mm_override", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            b_old = require_number(billet_weight_kg_per_mm_override, "press.billet_weight_kg_per_mm_override", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            if b_new != b_old:
                raise InvalidPressConfigurationError("billet_kg_per_mm_override and legacy billet_weight_kg_per_mm_override disagree")
        resolved_kg_per_mm_override = billet_kg_per_mm_override if billet_kg_per_mm_override is not None else billet_weight_kg_per_mm_override
        if resolved_kg_per_mm_override is not None:
            resolved_kg_per_mm_override = require_number(resolved_kg_per_mm_override, "press.billet_kg_per_mm_override", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)

        if billet_min_length_mm is not None and billet_min_mm is not None:
            bmin_new = require_number(billet_min_length_mm, "press.billet_min_length_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
            bmin_old = require_number(billet_min_mm, "press.billet_min_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
            if bmin_new != bmin_old:
                raise InvalidPressConfigurationError("billet_min_length_mm and legacy billet_min_mm disagree")
        if billet_max_length_mm is not None and billet_max_mm is not None:
            bmax_new = require_number(billet_max_length_mm, "press.billet_max_length_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
            bmax_old = require_number(billet_max_mm, "press.billet_max_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
            if bmax_new != bmax_old:
                raise InvalidPressConfigurationError("billet_max_length_mm and legacy billet_max_mm disagree")
        resolved_min = billet_min_length_mm if billet_min_length_mm is not None else billet_min_mm
        resolved_max = billet_max_length_mm if billet_max_length_mm is not None else billet_max_mm
        if resolved_min is not None:
            resolved_min = require_number(resolved_min, "press.billet_min_length_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
        if resolved_max is not None:
            resolved_max = require_number(resolved_max, "press.billet_max_length_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)

        nominal_source = "user_value"
        resolved_nominal = nominal_size_in
        if resolved_nominal is not None:
            resolved_nominal = float(require_int(resolved_nominal, "press.nominal_size_in", InvalidPressConfigurationError, minimum=6, maximum=16))
        elif billet_diameter_mm is not None:
            bd_for_class = require_number(billet_diameter_mm, "press.billet_diameter_mm", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
            import math
            inferred = int(math.floor(bd_for_class / 25.4 + 0.5))
            if not 6 <= inferred <= 16:
                raise InvalidPressConfigurationError("press inferred nominal size is outside the supported 6-16 inch range")
            resolved_nominal = float(inferred)
            nominal_source = "inferred_from_billet_diameter"
        else:
            nominal_source = "unavailable"

        billet_source = "user_value"
        resolved_billet = billet_diameter_mm
        if resolved_billet is None:
            if resolved_nominal is None:
                raise InvalidPressConfigurationError(
                    "billet_diameter_mm is required when nominal_size_in is not available"
                )
            resolved_billet = float(resolved_nominal) * 25.4
            billet_source = "inferred_from_nominal_size"

        container_source = "user_value"
        resolved_container = container_diameter_mm
        if resolved_container is None:
            resolved_container = float(resolved_billet) * DEFAULT_CONTAINER_DIAMETER_FACTOR
            container_source = "inferred_from_billet_diameter"

        limits_source = "user_value"
        if resolved_min is None or resolved_max is None:
            defaults = default_billet_limits(resolved_nominal)
            if defaults is None:
                raise InvalidPressConfigurationError(
                    "billet_min_length_mm and billet_max_length_mm are required when no documented nominal-size defaults exist"
                )
            default_min, default_max = defaults
            if resolved_min is None:
                resolved_min = default_min
            if resolved_max is None:
                resolved_max = default_max
            limits_source = "inferred_from_nominal_size"

        target_source = "user_value"
        resolved_target = target_net_productivity_kg_h
        if resolved_target is None:
            resolved_target = default_target_productivity_kg_h(resolved_nominal)
            target_source = "inferred_from_nominal_size" if resolved_target is not None else "unavailable"

        resolved_billet = require_number(resolved_billet, "press.billet_diameter_mm", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
        resolved_container = require_number(resolved_container, "press.container_diameter_mm", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
        if resolved_container <= resolved_billet:
            raise InvalidPressConfigurationError("press.container_diameter_mm must be greater than billet_diameter_mm")
        resolved_min = require_number(resolved_min, "press.billet_min_length_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
        resolved_max = require_number(resolved_max, "press.billet_max_length_mm", InvalidPressConfigurationError, minimum=100.0, maximum=3000.0)
        if resolved_min > resolved_max:
            raise InvalidPressConfigurationError("press.billet_min_length_mm must be <= billet_max_length_mm")
        if resolved_target is not None:
            resolved_target = require_number(resolved_target, "press.target_net_productivity_kg_h", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
        if billet_area_m2_override is not None:
            billet_area_m2_override = require_number(billet_area_m2_override, "press.billet_area_m2_override", InvalidPressConfigurationError, minimum=0.0, exclusive_minimum=True)
        if saws is not None and not isinstance(saws, SawSpec):
            raise InvalidPressConfigurationError("press.saws must be a SawSpec")
        if not isinstance(butt_rules, tuple) or any(not isinstance(rule, ButtRule) for rule in butt_rules):
            raise InvalidPressConfigurationError("press.butt_rules must be a tuple of ButtRule objects")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "table_length_m", table)
        object.__setattr__(self, "nominal_size_in", None if resolved_nominal is None else int(resolved_nominal))
        object.__setattr__(self, "billet_diameter_mm", float(resolved_billet))
        object.__setattr__(self, "container_diameter_mm", float(resolved_container))
        object.__setattr__(self, "billet_min_length_mm", float(resolved_min))
        object.__setattr__(self, "billet_max_length_mm", float(resolved_max))
        object.__setattr__(self, "dead_time_sec", dead_time)
        object.__setattr__(self, "density_kg_m3", float(resolved_density))
        object.__setattr__(self, "saws", saws if saws is not None else SawSpec())
        object.__setattr__(self, "target_net_productivity_kg_h", None if resolved_target is None else float(resolved_target))
        object.__setattr__(self, "press_force_t", None if resolved_force is None else float(resolved_force))
        object.__setattr__(self, "billet_area_m2_override", None if billet_area_m2_override is None else float(billet_area_m2_override))
        object.__setattr__(self, "billet_kg_per_mm_override", None if resolved_kg_per_mm_override is None else float(resolved_kg_per_mm_override))
        object.__setattr__(self, "butt_rules", tuple(butt_rules))

        object.__setattr__(self, "_nominal_size_source", nominal_source)
        object.__setattr__(self, "_billet_diameter_source", billet_source)
        object.__setattr__(self, "_container_diameter_source", container_source)
        object.__setattr__(self, "_billet_limits_source", limits_source)
        object.__setattr__(self, "_target_productivity_source", target_source)

        # Derived press geometry must remain representable as finite floats.
        import math
        for field_name, value in (
            ("press.container_area_m2", self.container_area_m2),
            ("press.billet_area_m2", self.billet_area_m2),
            ("press.billet_kg_per_mm", self.billet_weight_kg_per_mm),
        ):
            if not math.isfinite(value) or value <= 0:
                raise InvalidPressConfigurationError(
                    f"{field_name} is outside the supported finite numeric range"
                )

    # Historical compatibility aliases -------------------------------------------------
    @property
    def nominal_force_t(self) -> float | None:
        return self.press_force_t

    @property
    def billet_min_mm(self) -> float:
        return self.billet_min_length_mm

    @property
    def billet_max_mm(self) -> float:
        return self.billet_max_length_mm

    @property
    def aluminium_density_kg_m3(self) -> float:
        return self.density_kg_m3

    @property
    def billet_weight_kg_per_mm_override(self) -> float | None:
        return self.billet_kg_per_mm_override

    @property
    def recommended_min_linear_weight_kg_m(self) -> None:
        return None

    # Derived geometry and provenance --------------------------------------------------
    @property
    def container_area_m2(self) -> float:
        import math

        d_m = self.container_diameter_mm / 1000.0
        return math.pi * d_m * d_m / 4.0

    @property
    def billet_area_m2(self) -> float:
        """Actual billet area derived from billet diameter (v2.0 rule).

        ``billet_area_m2_override`` is retained only as a legacy input field and
        is intentionally not used by the v2.4 engine. A measured mass
        coefficient should use ``billet_kg_per_mm_override`` instead.
        """
        import math

        d_m = self.billet_diameter_mm / 1000.0
        return math.pi * d_m * d_m / 4.0

    @property
    def billet_weight_kg_per_mm(self) -> float:
        if self.billet_kg_per_mm_override is not None:
            return self.billet_kg_per_mm_override
        return self.billet_area_m2 * self.density_kg_m3 / 1000.0

    @property
    def nominal_size_source(self) -> str:
        return self._nominal_size_source

    @property
    def billet_diameter_source(self) -> str:
        return self._billet_diameter_source

    @property
    def container_diameter_source(self) -> str:
        return self._container_diameter_source

    @property
    def billet_limits_source(self) -> str:
        return self._billet_limits_source

    @property
    def target_productivity_source(self) -> str:
        return self._target_productivity_source

    def resolve_butt_mm(self, profile_type: ProfileType, kg_m_total: float) -> tuple[float, str]:
        canonical = normalize_profile_type(profile_type)
        for rule in self.butt_rules:
            if rule.matches(canonical, kg_m_total):
                return float(rule.butt_mm), "user_override"
        return DEFAULT_BUTT_MM[canonical], "default_rule"

    def butt_mm_for(self, profile_type: ProfileType, kg_m_total: float) -> float:
        """Compatibility helper returning only the resolved butt length."""
        return self.resolve_butt_mm(profile_type, kg_m_total)[0]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "nominal_size_in": self.nominal_size_in,
            "billet_diameter_mm": self.billet_diameter_mm,
            "container_diameter_mm": self.container_diameter_mm,
            "billet_min_length_mm": self.billet_min_length_mm,
            "billet_max_length_mm": self.billet_max_length_mm,
            "table_length_m": self.table_length_m,
            "dead_time_sec": self.dead_time_sec,
            "density_kg_m3": self.density_kg_m3,
            "saws": asdict(self.saws),
            "target_net_productivity_kg_h": self.target_net_productivity_kg_h,
            "press_force_t": self.press_force_t,
            "billet_kg_per_mm_override": self.billet_kg_per_mm_override,
        }
        if self.butt_rules:
            data["butt_rules"] = [asdict(rule) for rule in self.butt_rules]
        return data


@dataclass(frozen=True)
class ProfileSpec:
    linear_weight_kg_m: float
    exits: int = 1
    profile_type: ProfileType | None = None
    section_per_exit_m2: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "linear_weight_kg_m", require_number(self.linear_weight_kg_m, "profile.linear_weight_kg_m", InvalidProfileInputError, minimum=0.0, exclusive_minimum=True))
        object.__setattr__(self, "exits", require_int(self.exits, "profile.exits", InvalidProfileInputError, minimum=1))
        object.__setattr__(self, "profile_type", normalize_profile_type(self.profile_type))
        if self.section_per_exit_m2 is not None:
            object.__setattr__(self, "section_per_exit_m2", require_number(self.section_per_exit_m2, "profile.section_per_exit_m2", InvalidProfileInputError, minimum=0.0, exclusive_minimum=True))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessSpec:
    """Quantity-free process conditions for planning and process evaluation."""

    exit_speed_m_min: float | None
    cut_length_mm: float
    front_scrap_m: float = 0.0
    complexity: Complexity = "normal"
    cuts: int | None = None
    butt_mm: float | None = None
    multi_billet_front_scrap_m: float | None = None
    ram_speed_mm_s: float | None = None

    def __post_init__(self) -> None:
        if (self.exit_speed_m_min is None) == (self.ram_speed_mm_s is None):
            raise InvalidProductionInputError("process must define exactly one of exit_speed_m_min or ram_speed_mm_s")
        if self.exit_speed_m_min is not None:
            object.__setattr__(self, "exit_speed_m_min", require_number(self.exit_speed_m_min, "process.exit_speed_m_min", InvalidProductionInputError, minimum=1.0, maximum=100.0))
        if self.ram_speed_mm_s is not None:
            object.__setattr__(self, "ram_speed_mm_s", require_number(self.ram_speed_mm_s, "process.ram_speed_mm_s", InvalidProductionInputError, minimum=0.0, exclusive_minimum=True))
        object.__setattr__(self, "cut_length_mm", require_number(self.cut_length_mm, "process.cut_length_mm", InvalidProductionInputError, minimum=1000.0, maximum=15000.0))
        object.__setattr__(self, "front_scrap_m", require_number(self.front_scrap_m, "process.front_scrap_m", InvalidProductionInputError, minimum=0.0))
        if self.complexity not in {"normal", "medium", "high"}:
            raise InvalidProductionInputError("process.complexity must be normal, medium or high")
        if self.cuts is not None:
            object.__setattr__(self, "cuts", require_int(self.cuts, "process.cuts", InvalidProductionInputError, minimum=1))
        if self.butt_mm is not None:
            object.__setattr__(self, "butt_mm", require_number(self.butt_mm, "process.butt_mm", InvalidProductionInputError, minimum=0.0))
        if self.multi_billet_front_scrap_m is not None:
            object.__setattr__(self, "multi_billet_front_scrap_m", require_number(self.multi_billet_front_scrap_m, "process.multi_billet_front_scrap_m", InvalidProductionInputError, minimum=0.0))

    @classmethod
    def from_ram_speed(cls, *, ram_speed_mm_s: float, cut_length_mm: float, **kwargs: Any) -> "ProcessSpec":
        return cls(exit_speed_m_min=None, cut_length_mm=cut_length_mm, ram_speed_mm_s=ram_speed_mm_s, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanningCase:
    """Profile + process definition without an order quantity."""

    profile: ProfileSpec
    process: ProcessSpec

    def to_dict(self, *, schema_version: str = "1.1") -> dict[str, Any]:
        return {
            "schema_version": schema_version,
            "profile": self.profile.to_dict(),
            "process": self.process.to_dict(),
        }

    def with_profile(self, **changes: Any) -> "PlanningCase":
        valid = {f.name for f in dataclass_fields(ProfileSpec)}
        unknown = sorted(set(changes) - valid)
        if unknown:
            raise InvalidStudyAdjustmentError(
                f"Unknown profile adjustment field(s): {', '.join(unknown)}. "
                f"Valid fields: {', '.join(sorted(valid))}"
            )
        return dataclass_replace(self, profile=dataclass_replace(self.profile, **changes))

    def with_process(self, **changes: Any) -> "PlanningCase":
        valid = {f.name for f in dataclass_fields(ProcessSpec)}
        unknown = sorted(set(changes) - valid)
        if unknown:
            raise InvalidStudyAdjustmentError(
                f"Unknown process adjustment field(s): {', '.join(unknown)}. "
                f"Valid fields: {', '.join(sorted(valid))}"
            )
        return dataclass_replace(self, process=dataclass_replace(self.process, **changes))

    def to_process_input(self, press: PressSpec) -> "ProcessInput":
        q = self.process
        return ProcessInput(
            press=press,
            profile=self.profile,
            exit_speed_m_min=q.exit_speed_m_min,
            cut_length_mm=q.cut_length_mm,
            front_scrap_m=q.front_scrap_m,
            complexity=q.complexity,
            cuts=q.cuts,
            butt_mm=q.butt_mm,
            multi_billet_front_scrap_m=q.multi_billet_front_scrap_m,
            ram_speed_mm_s=q.ram_speed_mm_s,
        )

    def to_study_case(self, bars_requested: int = 1, *, supplement_10_pct: bool = False) -> "StudyCase":
        q = self.process
        return StudyCase(
            profile=self.profile,
            production=ProductionSpec(
                exit_speed_m_min=q.exit_speed_m_min,
                cut_length_mm=q.cut_length_mm,
                bars_requested=bars_requested,
                front_scrap_m=q.front_scrap_m,
                complexity=q.complexity,
                cuts=q.cuts,
                butt_mm=q.butt_mm,
                multi_billet_front_scrap_m=q.multi_billet_front_scrap_m,
                supplement_10_pct=supplement_10_pct,
                ram_speed_mm_s=q.ram_speed_mm_s,
            ),
        )


@dataclass(frozen=True)
class ProductionSpec:
    """Production inputs independent from a particular press."""

    exit_speed_m_min: float | None
    cut_length_mm: float
    bars_requested: int
    front_scrap_m: float = 0.0
    complexity: Complexity = "normal"
    cuts: int | None = None
    butt_mm: float | None = None
    multi_billet_front_scrap_m: float | None = None
    supplement_10_pct: bool = False
    ram_speed_mm_s: float | None = None

    def __post_init__(self) -> None:
        if (self.exit_speed_m_min is None) == (self.ram_speed_mm_s is None):
            raise InvalidProductionInputError("production must define exactly one of exit_speed_m_min or ram_speed_mm_s")
        if self.exit_speed_m_min is not None:
            object.__setattr__(self, "exit_speed_m_min", require_number(self.exit_speed_m_min, "production.exit_speed_m_min", InvalidProductionInputError, minimum=1.0, maximum=100.0))
        if self.ram_speed_mm_s is not None:
            object.__setattr__(self, "ram_speed_mm_s", require_number(self.ram_speed_mm_s, "production.ram_speed_mm_s", InvalidProductionInputError, minimum=0.0, exclusive_minimum=True))
        object.__setattr__(self, "cut_length_mm", require_number(self.cut_length_mm, "production.cut_length_mm", InvalidProductionInputError, minimum=1000.0, maximum=15000.0))
        object.__setattr__(self, "bars_requested", require_int(self.bars_requested, "production.bars_requested", InvalidProductionInputError, minimum=1))
        object.__setattr__(self, "front_scrap_m", require_number(self.front_scrap_m, "production.front_scrap_m", InvalidProductionInputError, minimum=0.0))
        if self.complexity not in {"normal", "medium", "high"}:
            raise InvalidProductionInputError("production.complexity must be normal, medium or high")
        if self.cuts is not None:
            object.__setattr__(self, "cuts", require_int(self.cuts, "production.cuts", InvalidProductionInputError, minimum=1))
        if self.butt_mm is not None:
            object.__setattr__(self, "butt_mm", require_number(self.butt_mm, "production.butt_mm", InvalidProductionInputError, minimum=0.0))
        if self.multi_billet_front_scrap_m is not None:
            object.__setattr__(self, "multi_billet_front_scrap_m", require_number(self.multi_billet_front_scrap_m, "production.multi_billet_front_scrap_m", InvalidProductionInputError, minimum=0.0))
        object.__setattr__(self, "supplement_10_pct", require_bool(self.supplement_10_pct, "production.supplement_10_pct", InvalidProductionInputError))

    @classmethod
    def from_ram_speed(cls, *, ram_speed_mm_s: float, cut_length_mm: float, bars_requested: int, **kwargs: Any) -> "ProductionSpec":
        return cls(exit_speed_m_min=None, cut_length_mm=cut_length_mm, bars_requested=bars_requested, ram_speed_mm_s=ram_speed_mm_s, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StudyCase:
    """Reusable immutable profile + production case."""

    profile: ProfileSpec
    production: ProductionSpec

    def to_dict(self, *, schema_version: str = "1.1") -> dict[str, Any]:
        return {
            "schema_version": schema_version,
            "profile": self.profile.to_dict(),
            "production": self.production.to_dict(),
        }

    def with_profile(self, **changes: Any) -> "StudyCase":
        valid = {f.name for f in dataclass_fields(ProfileSpec)}
        unknown = sorted(set(changes) - valid)
        if unknown:
            raise InvalidStudyAdjustmentError(
                f"Unknown profile adjustment field(s): {', '.join(unknown)}. "
                f"Valid fields: {', '.join(sorted(valid))}"
            )
        return dataclass_replace(self, profile=dataclass_replace(self.profile, **changes))

    def with_production(self, **changes: Any) -> "StudyCase":
        valid = {f.name for f in dataclass_fields(ProductionSpec)}
        unknown = sorted(set(changes) - valid)
        if unknown:
            raise InvalidStudyAdjustmentError(
                f"Unknown production adjustment field(s): {', '.join(unknown)}. "
                f"Valid fields: {', '.join(sorted(valid))}"
            )
        return dataclass_replace(self, production=dataclass_replace(self.production, **changes))

    def replace(self, **changes: Any) -> "StudyCase":
        profile_fields = {f.name for f in dataclass_fields(ProfileSpec)}
        production_fields = {f.name for f in dataclass_fields(ProductionSpec)}
        unknown = sorted(set(changes) - profile_fields - production_fields)
        if unknown:
            raise InvalidStudyAdjustmentError(
                f"Unknown StudyCase adjustment field(s): {', '.join(unknown)}"
            )
        profile_changes = {k: v for k, v in changes.items() if k in profile_fields}
        production_changes = {k: v for k, v in changes.items() if k in production_fields}
        out = self
        if profile_changes:
            out = out.with_profile(**profile_changes)
        if production_changes:
            out = out.with_production(**production_changes)
        return out

    def to_planning_case(self) -> PlanningCase:
        p = self.production
        return PlanningCase(
            profile=self.profile,
            process=ProcessSpec(
                exit_speed_m_min=p.exit_speed_m_min,
                cut_length_mm=p.cut_length_mm,
                front_scrap_m=p.front_scrap_m,
                complexity=p.complexity,
                cuts=p.cuts,
                butt_mm=p.butt_mm,
                multi_billet_front_scrap_m=p.multi_billet_front_scrap_m,
                ram_speed_mm_s=p.ram_speed_mm_s,
            ),
        )

    def to_study_input(self, press: PressSpec) -> "StudyInput":
        p = self.production
        return StudyInput(
            press=press,
            profile=self.profile,
            exit_speed_m_min=p.exit_speed_m_min,
            cut_length_mm=p.cut_length_mm,
            bars_requested=p.bars_requested,
            front_scrap_m=p.front_scrap_m,
            complexity=p.complexity,
            cuts=p.cuts,
            butt_mm=p.butt_mm,
            multi_billet_front_scrap_m=p.multi_billet_front_scrap_m,
            supplement_10_pct=p.supplement_10_pct,
            ram_speed_mm_s=p.ram_speed_mm_s,
        )


@dataclass(frozen=True)
class ProcessInput:
    """Internal/public quantity-free input resolved from Press + PlanningCase."""

    press: PressSpec
    profile: ProfileSpec
    exit_speed_m_min: float | None
    cut_length_mm: float
    front_scrap_m: float = 0.0
    complexity: Complexity = "normal"
    cuts: int | None = None
    butt_mm: float | None = None
    multi_billet_front_scrap_m: float | None = None
    ram_speed_mm_s: float | None = None


@dataclass(frozen=True)
class StudyInput:
    press: PressSpec
    profile: ProfileSpec
    exit_speed_m_min: float | None
    cut_length_mm: float
    bars_requested: int
    front_scrap_m: float = 0.0
    complexity: Complexity = "normal"
    cuts: int | None = None
    butt_mm: float | None = None
    multi_billet_front_scrap_m: float | None = None
    supplement_10_pct: bool = False
    effective_bars_target_override: int | None = None
    ram_speed_mm_s: float | None = None

    def to_case(self) -> StudyCase:
        return StudyCase(
            profile=self.profile,
            production=ProductionSpec(
                exit_speed_m_min=self.exit_speed_m_min,
                cut_length_mm=self.cut_length_mm,
                bars_requested=self.bars_requested,
                front_scrap_m=self.front_scrap_m,
                complexity=self.complexity,
                cuts=self.cuts,
                butt_mm=self.butt_mm,
                multi_billet_front_scrap_m=self.multi_billet_front_scrap_m,
                supplement_10_pct=self.supplement_10_pct,
                ram_speed_mm_s=self.ram_speed_mm_s,
            ),
        )


@dataclass(frozen=True)
class ConfigurationResult(_ResultBlock):
    name: ConfigurationName
    priority: int
    valid: bool
    billets_per_configuration: int
    profiles_per_configuration: int
    cuts: int
    front_scrap_per_billet_m: float
    front_scrap_source: str
    length_per_profile_m: float
    length_per_billet_m: float
    total_configuration_length_m: float
    table_occupancy_length_m: float
    billet_useful_length_mm: float
    billet_length_mm: float
    billets_per_pull: int = 1
    profiles_per_billet: int = 1
    cuts_per_pull: int = 0
    bars_per_pull: int = 0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessResult:
    """Quantity-free evaluation of Press + Profile + ProcessSpec.

    This is the preferred reference object for planning integrations. It
    contains geometry, billet optimisation, supported configuration and
    per-billet/per-pull capacity, but no order quantity.
    """

    viable: bool
    supported: bool
    unsupported_reason: str | None
    required_profiles_per_billet: int | None
    press_name: str
    recommended_configuration: ConfigurationName | None
    valid_configurations: tuple[ConfigurationName, ...]
    configurations: tuple[ConfigurationResult, ...]
    profile_section_per_exit_m2: float
    profile_section_total_m2: float
    extrusion_ratio: float
    extrusion_ratio_status: str
    exit_speed_m_min: float
    ram_speed_m_min: float
    ram_speed_mm_s: float
    speed_input_source: str
    theoretical_cuts: int
    cuts: int
    cuts_per_pull: int
    billets_per_pull: int
    profiles_per_billet: int
    bars_per_billet: int
    bars_per_pull: int
    pull_length_m: float
    profile_pull_length_m: float
    extruded_length_per_billet_m: float
    table_occupancy_length_m: float
    configuration_total_length_m: float
    table_ratio: float
    billet_ratio: float
    cuts_ratio: float
    geometric_index: float
    butt_mm: float
    butt_source: str
    billet_useful_length_mm: float
    billet_length_mm: float
    recommended_billet_length_mm: int
    billet_kg_per_mm: float
    applied_front_scrap_m: float
    applied_front_scrap_source: str
    cuts_source: str
    extrusion_time_per_billet_min: float
    dead_time_sec: float
    warnings: tuple[str, ...] = ()

    @property
    def first_billet_time_min(self) -> float:
        dead = self.dead_time_sec / 60.0 if self.profiles_per_billet == 2 else 0.0
        return self.extrusion_time_per_billet_min + dead

    @property
    def total_time_min(self) -> float:
        """Deprecated compatibility alias for first_billet_time_min."""
        return self.first_billet_time_min

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = {
            "viable": self.viable,
            "supported": self.supported,
            "unsupported_reason": self.unsupported_reason,
            "required_profiles_per_billet": self.required_profiles_per_billet,
            "recommended_configuration": self.recommended_configuration,
        }
        data["first_billet_time_min"] = self.first_billet_time_min
        return data

    def to_json(self, *, indent: int | None = None) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class StatusResult(_ResultBlock):
    viable: bool
    supported: bool
    unsupported_reason: str | None
    required_profiles_per_billet: int | None
    recommended_configuration: ConfigurationName | None


@dataclass(frozen=True)
class GeometryResult(_ResultBlock):
    profile_section_per_exit_m2: float
    profile_section_total_m2: float
    container_area_m2: float
    billet_area_m2: float
    extrusion_ratio: float
    extrusion_ratio_status: str
    exit_speed_m_min: float
    ram_speed_m_min: float
    ram_speed_mm_s: float
    theoretical_cuts: int
    cuts: int
    cuts_per_pull: int
    billets_per_pull: int
    profiles_per_billet: int
    pull_length_m: float
    profile_pull_length_m: float
    extruded_length_per_billet_m: float
    table_occupancy_length_m: float
    configuration_total_length_m: float
    table_ratio: float
    billet_ratio: float
    cuts_ratio: float
    geometric_index: float


@dataclass(frozen=True)
class BilletResult(_ResultBlock):
    useful_length_mm: float
    length_mm: float
    recommended_length_mm: int
    count: int
    butt_mm: float
    butt_source: str
    kg_per_mm: float


@dataclass(frozen=True)
class ProductionResult(_ResultBlock):
    profiles_per_billet: int
    billets_per_pull: int
    cuts_per_pull: int
    bars_per_pull: int
    bars_per_billet: int
    billets: int
    full_pulls: int
    remaining_billets: int
    n_pulls: int
    bars_requested: int
    bars_target_effective: int
    supplement_10_pct: bool
    supplement_factor: float
    bars_manufactured: int
    extra_bars: int
    extra_pct: float
    good_kg_requested: float
    good_kg_effective_target: float
    good_kg_manufactured: float


@dataclass(frozen=True)
class ScrapResult(_ResultBlock):
    start_kg: float
    complexity_kg: float
    butt_kg: float
    front_scrap_kg: float
    billet_saw_kg: float
    puller_saw_kg: float
    final_saw_kg: float
    fixed_kg: float
    fixed_pct: float
    total_kg: float
    total_pct: float
    extruded_losses_kg: float


@dataclass(frozen=True)
class ProductivityResult(_ResultBlock):
    nominal_gross_kg_h: float
    real_gross_kg_h: float
    real_net_kg_h: float
    extruded_total_kg: float
    target_net_kg_h: float | None
    target_source: str
    ratio: float | None
    delta_kg_h: float | None
    deficit_pct: float | None
    relative_score: float | None
    fixed_scrap_score: float | None
    penalty_points: float | None
    productivity_index: float | None
    productivity_index_rating: str | None


@dataclass(frozen=True)
class TimingResult(_ResultBlock):
    extrusion_per_billet_min: float
    extrusion_total_min: float
    dead_time_events: int
    dead_time_total_min: float
    total_min: float
    cycle_per_billet_min: float
    total_hours: float


@dataclass(frozen=True)
class ProcessTraceResult(_ResultBlock):
    butt_source: str
    standard_front_scrap_m: float
    multi_billet_front_scrap_m: float
    multi_billet_front_scrap_source: str
    applied_front_scrap_m: float
    applied_front_scrap_source: str
    cuts_source: str
    speed_input_source: str
    supplement_10_pct: bool
    supplement_factor: float
    target_productivity_source: str


@dataclass(frozen=True)
class CalculationResult:
    # Flat compatibility fields --------------------------------------------------------
    viable: bool
    supported: bool
    unsupported_reason: str | None
    required_profiles_per_billet: int | None
    press_name: str
    recommended_configuration: ConfigurationName | None
    valid_configurations: tuple[ConfigurationName, ...]
    configurations: tuple[ConfigurationResult, ...]
    profile_section_per_exit_m2: float
    profile_section_total_m2: float
    extrusion_ratio: float
    extrusion_ratio_status: str
    exit_speed_m_min: float
    ram_speed_m_min: float
    ram_speed_mm_s: float
    theoretical_cuts: int
    cuts: int
    cuts_per_pull: int
    billets_per_pull: int
    profiles_per_billet: int
    n_pulls: int
    full_pulls: int
    remaining_billets: int
    bars_per_pull: int
    pull_length_m: float
    profile_pull_length_m: float
    extruded_length_per_billet_m: float
    table_occupancy_length_m: float
    configuration_total_length_m: float
    butt_mm: float
    billet_useful_length_mm: float
    billet_length_mm: float
    recommended_billet_length_mm: int
    bars_per_billet: int
    billets: int
    bars_target_effective: int
    supplement_10_pct: bool
    bars_manufactured: int
    extra_bars: int
    extra_pct: float
    good_kg_requested: float
    good_kg_effective_target: float
    good_kg_manufactured: float
    fixed_scrap_kg: float
    fixed_scrap_pct: float
    global_scrap_kg: float
    global_scrap_pct: float
    nominal_gross_kg_h: float
    real_gross_kg_h: float
    real_net_kg_h: float
    target_net_productivity_kg_h: float | None
    productivity_ratio: float | None
    productivity_deficit_pct: float | None
    productivity_index: float | None
    extrusion_time_per_billet_min: float
    extrusion_time_total_min: float
    dead_time_events: int
    dead_time_total_min: float
    total_time_min: float
    cycle_time_per_billet_min: float
    table_ratio: float
    billet_ratio: float
    cuts_ratio: float
    geometric_index: float

    # Structured result blocks ---------------------------------------------------------
    status: StatusResult
    geometry: GeometryResult
    billet: BilletResult
    production: ProductionResult
    scrap: ScrapResult
    productivity: ProductivityResult
    timing: TimingResult
    process: ProcessTraceResult
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int | None = None) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)

    def value(self, path: str) -> Any:
        if not path or not isinstance(path, str):
            raise InvalidResultSelectionError("field path must be a non-empty string")
        current: Any = self
        for part in path.split("."):
            if is_dataclass(current):
                if not hasattr(current, part):
                    raise UnknownResultFieldError(f"Unknown result field: {path}")
                current = getattr(current, part)
            elif isinstance(current, dict):
                if part not in current:
                    raise UnknownResultFieldError(f"Unknown result field: {path}")
                current = current[part]
            else:
                raise UnknownResultFieldError(f"Unknown result field: {path}")
        return current

    def __getitem__(self, path: str) -> Any:
        return self.value(path)

    def select(self, *paths: str) -> dict[str, Any]:
        if not paths:
            raise InvalidResultSelectionError("select() requires at least one field path")
        return {path: self.value(path) for path in paths}

    def section(self, name: str) -> dict[str, Any]:
        if name not in RESULT_SECTIONS:
            raise UnknownResultSectionError(f"Unknown result section: {name}")
        block = getattr(self, name)
        return block.to_dict()

    def field_paths(self) -> tuple[str, ...]:
        return tuple(item.path for item in list_fields())


@dataclass(frozen=True)
class ComparisonResult:
    """Results for the same StudyCase evaluated on multiple presses.

    PyExtrusion exposes the v2.4 productivity index for comparison, but still
    does not make an automatic final industrial decision for the user.
    """

    results: tuple[CalculationResult, ...]

    @property
    def viable_results(self) -> tuple[CalculationResult, ...]:
        return tuple(r for r in self.results if r.viable)

    @property
    def viable_press_names(self) -> tuple[str, ...]:
        return tuple(r.press_name for r in self.viable_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "press_count": len(self.results),
            "viable_press_count": len(self.viable_results),
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)
