from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .._strict import require_number, require_string
from .mechanics import circular_area_m2_from_diameter_mm
from .metadata import SourceRef

ForceLimitSource = Literal["caller_supplied", "operating_force_limit", "rated_force"]
InstalledPowerKind = Literal[
    "electrical_input",
    "motor_shaft",
    "hydraulic_output",
    "aggregate_nameplate",
]


def _optional_positive(value: float | None, field: str) -> float | None:
    if value is None:
        return None
    result = require_number(value, field, ValueError, minimum=0.0, exclusive_minimum=True)
    assert result is not None
    return result


def _validated_provenance(items: tuple[SourceRef, ...]) -> tuple[SourceRef, ...]:
    provenance = tuple(items)
    if any(not isinstance(item, SourceRef) for item in provenance):
        raise ValueError("engineering provenance entries must be SourceRef instances")
    return provenance


@dataclass(frozen=True)
class RamOperatingRange:
    """Configured ram-speed interval.

    This object stores scalar machine limits only. It does not predict ram
    speed, infer a suitable process speed, or assert that every speed in the
    interval is sustainable at every configured force.
    """

    minimum_mm_s: float
    maximum_mm_s: float

    def __post_init__(self) -> None:
        minimum = require_number(self.minimum_mm_s, "ram minimum_mm_s", ValueError, minimum=0.0)
        maximum = require_number(self.maximum_mm_s, "ram maximum_mm_s", ValueError, minimum=0.0)
        assert minimum is not None and maximum is not None
        if minimum > maximum:
            raise ValueError("ram minimum_mm_s must be <= maximum_mm_s")
        object.__setattr__(self, "minimum_mm_s", minimum)
        object.__setattr__(self, "maximum_mm_s", maximum)

    def contains(self, speed_mm_s: float) -> bool:
        speed = require_number(speed_mm_s, "ram speed_mm_s", ValueError, minimum=0.0)
        assert speed is not None
        return self.minimum_mm_s <= speed <= self.maximum_mm_s

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class HydraulicSystemSpec:
    """Optional independently documented hydraulic-system quantities.

    These fields are not an operating envelope. PyExtrusion does not assume
    that pressure, flow, area and installed power belong to one actuator, one
    pump or one simultaneous operating point.

    ``pressure_force_area_m2`` is an area associated with one explicitly
    interpreted ``p A`` force contribution; it is not automatically the net
    ram effective area. ``installed_power_kind`` is required whenever installed
    power is supplied so the energy boundary is not left implicit.
    """

    pressure_force_area_m2: float | None = None
    max_pressure_bar: float | None = None
    max_flow_l_min: float | None = None
    installed_power_kw: float | None = None
    installed_power_kind: InstalledPowerKind | None = None
    provenance: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pressure_force_area_m2",
            _optional_positive(self.pressure_force_area_m2, "hydraulic pressure_force_area_m2"),
        )
        object.__setattr__(
            self,
            "max_pressure_bar",
            _optional_positive(self.max_pressure_bar, "hydraulic max_pressure_bar"),
        )
        object.__setattr__(
            self,
            "max_flow_l_min",
            _optional_positive(self.max_flow_l_min, "hydraulic max_flow_l_min"),
        )
        installed_power = _optional_positive(self.installed_power_kw, "hydraulic installed_power_kw")
        object.__setattr__(self, "installed_power_kw", installed_power)

        valid_power_kinds = {
            "electrical_input",
            "motor_shaft",
            "hydraulic_output",
            "aggregate_nameplate",
        }
        if installed_power is not None:
            if self.installed_power_kind not in valid_power_kinds:
                raise ValueError("installed_power_kind is required when installed_power_kw is provided")
        elif self.installed_power_kind is not None:
            raise ValueError("installed_power_kind requires installed_power_kw")

        object.__setattr__(self, "provenance", _validated_provenance(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PressEngineeringSpec:
    """Press-specific engineering data supplied as explicit configuration.

    The model intentionally separates universal equations from machine data.
    It stores documented or user-supplied scalar limits and does not invent a
    predictive extrusion-force, pressure, friction, hydraulic-envelope or
    thermal model.
    """

    press_id: str
    container_diameter_mm: float
    rated_force_mn: float | None = None
    operating_force_limit_mn: float | None = None
    ram_speed_range: RamOperatingRange | None = None
    hydraulic_system: HydraulicSystemSpec | None = None
    provenance: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        press_id = require_string(self.press_id, "press_id", ValueError).strip()
        if not press_id:
            raise ValueError("press_id must be a non-empty string")
        container_diameter = require_number(
            self.container_diameter_mm,
            "container_diameter_mm",
            ValueError,
            minimum=0.0,
            exclusive_minimum=True,
        )
        assert container_diameter is not None
        rated_force = _optional_positive(self.rated_force_mn, "rated_force_mn")
        operating_limit = _optional_positive(self.operating_force_limit_mn, "operating_force_limit_mn")
        if rated_force is not None and operating_limit is not None and operating_limit > rated_force:
            raise ValueError("operating_force_limit_mn cannot exceed rated_force_mn")
        if self.ram_speed_range is not None and not isinstance(self.ram_speed_range, RamOperatingRange):
            raise ValueError("ram_speed_range must be a RamOperatingRange when provided")
        if self.hydraulic_system is not None and not isinstance(self.hydraulic_system, HydraulicSystemSpec):
            raise ValueError("hydraulic_system must be a HydraulicSystemSpec when provided")

        object.__setattr__(self, "press_id", press_id)
        object.__setattr__(self, "container_diameter_mm", container_diameter)
        object.__setattr__(self, "rated_force_mn", rated_force)
        object.__setattr__(self, "operating_force_limit_mn", operating_limit)
        object.__setattr__(self, "provenance", _validated_provenance(self.provenance))

    @property
    def container_area_m2(self) -> float:
        """Internal container-bore area from the configured diameter."""
        return circular_area_m2_from_diameter_mm(self.container_diameter_mm)

    @property
    def configured_force_limit_mn(self) -> float | None:
        """Return the configured comparison limit with no hidden derating."""
        if self.operating_force_limit_mn is not None:
            return self.operating_force_limit_mn
        return self.rated_force_mn

    @property
    def configured_force_limit_source(self) -> ForceLimitSource | None:
        """Identify which configured scalar supplied the force limit."""
        if self.operating_force_limit_mn is not None:
            return "operating_force_limit"
        if self.rated_force_mn is not None:
            return "rated_force"
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForceCapacityCheck:
    """Arithmetic comparison of required force with a configured scalar limit.

    This object does not prove that the limit is physically available at a
    particular speed, stroke position, duration or hydraulic operating mode.
    Derived fields are properties so contradictory combinations cannot be
    supplied directly by callers.
    """

    required_force_mn: float
    configured_force_limit_mn: float
    limit_source: ForceLimitSource = "caller_supplied"

    def __post_init__(self) -> None:
        required = require_number(self.required_force_mn, "required_force_mn", ValueError, minimum=0.0)
        limit = require_number(
            self.configured_force_limit_mn,
            "configured_force_limit_mn",
            ValueError,
            minimum=0.0,
            exclusive_minimum=True,
        )
        assert required is not None and limit is not None
        if self.limit_source not in {"caller_supplied", "operating_force_limit", "rated_force"}:
            raise ValueError(f"unsupported force limit source: {self.limit_source!r}")
        utilization = required / limit
        if not math.isfinite(utilization):
            raise ValueError("force utilization is outside the representable finite range")
        object.__setattr__(self, "required_force_mn", required)
        object.__setattr__(self, "configured_force_limit_mn", limit)

    @property
    def margin_mn(self) -> float:
        return self.configured_force_limit_mn - self.required_force_mn

    @property
    def utilization(self) -> float:
        return self.required_force_mn / self.configured_force_limit_mn

    @property
    def within_limit(self) -> bool:
        return self.required_force_mn <= self.configured_force_limit_mn

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_force_mn": self.required_force_mn,
            "configured_force_limit_mn": self.configured_force_limit_mn,
            "limit_source": self.limit_source,
            "margin_mn": self.margin_mn,
            "utilization": self.utilization,
            "within_limit": self.within_limit,
        }


def check_force_capacity(
    required_force_mn: float,
    configured_force_limit_mn: float,
    *,
    limit_source: ForceLimitSource = "caller_supplied",
) -> ForceCapacityCheck:
    """Compare a supplied force with a supplied configured scalar limit.

    This is an accounting comparison, not a predictive extrusion-force or
    hydraulic-capability model. A positive margin is not a safety factor.
    """
    return ForceCapacityCheck(
        required_force_mn=required_force_mn,
        configured_force_limit_mn=configured_force_limit_mn,
        limit_source=limit_source,
    )


def check_press_force_capacity(required_force_mn: float, press: PressEngineeringSpec) -> ForceCapacityCheck:
    """Compare a supplied force with the press's explicitly configured limit."""
    if not isinstance(press, PressEngineeringSpec):
        raise ValueError("press must be a PressEngineeringSpec")
    force_limit = press.configured_force_limit_mn
    force_source = press.configured_force_limit_source
    if force_limit is None or force_source is None:
        raise ValueError("press has no configured force limit")
    return check_force_capacity(required_force_mn, force_limit, limit_source=force_source)
