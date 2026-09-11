from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number, require_string
from .mechanics import circular_area_m2_from_diameter_mm
from .metadata import SourceRef


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

    This object stores a machine limit only. It does not predict ram speed or
    infer a suitable process speed from profile geometry or alloy data.
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
    """Optional documented hydraulic-system limits.

    The fields are deliberately independent. PyExtrusion does not assume that
    one pump, one cylinder or one pressure stage represents the whole press.
    No force, flow or power capability is inferred automatically from this
    configuration.
    """

    effective_area_m2: float | None = None
    max_pressure_bar: float | None = None
    max_flow_l_min: float | None = None
    installed_power_kw: float | None = None
    provenance: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_area_m2", _optional_positive(self.effective_area_m2, "hydraulic effective_area_m2"))
        object.__setattr__(self, "max_pressure_bar", _optional_positive(self.max_pressure_bar, "hydraulic max_pressure_bar"))
        object.__setattr__(self, "max_flow_l_min", _optional_positive(self.max_flow_l_min, "hydraulic max_flow_l_min"))
        object.__setattr__(self, "installed_power_kw", _optional_positive(self.installed_power_kw, "hydraulic installed_power_kw"))
        object.__setattr__(self, "provenance", _validated_provenance(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PressEngineeringSpec:
    """Press-specific engineering data supplied as explicit configuration.

    The model intentionally separates universal equations from machine data.
    It stores only documented or user-supplied limits and does not invent a
    predictive extrusion-force, pressure, friction or thermal model.
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
        """Return the explicit operating limit, falling back to rated force.

        No derating factor or safety factor is introduced by PyExtrusion.
        """
        if self.operating_force_limit_mn is not None:
            return self.operating_force_limit_mn
        return self.rated_force_mn

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForceCapacityCheck:
    """Direct comparison between an externally supplied force and a limit."""

    required_force_mn: float
    available_force_mn: float
    margin_mn: float
    utilization: float
    within_limit: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_force_capacity(required_force_mn: float, available_force_mn: float) -> ForceCapacityCheck:
    """Compare a supplied required force against a supplied available force.

    This is an accounting identity, not a predictive extrusion-force model.
    The caller remains responsible for how ``required_force_mn`` was obtained.
    """
    required = require_number(required_force_mn, "required_force_mn", ValueError, minimum=0.0)
    available = require_number(
        available_force_mn,
        "available_force_mn",
        ValueError,
        minimum=0.0,
        exclusive_minimum=True,
    )
    assert required is not None and available is not None
    return ForceCapacityCheck(
        required_force_mn=required,
        available_force_mn=available,
        margin_mn=available - required,
        utilization=required / available,
        within_limit=required <= available,
    )


def check_press_force_capacity(required_force_mn: float, press: PressEngineeringSpec) -> ForceCapacityCheck:
    """Compare a supplied force with the press's explicitly configured limit."""
    if not isinstance(press, PressEngineeringSpec):
        raise ValueError("press must be a PressEngineeringSpec")
    force_limit = press.configured_force_limit_mn
    if force_limit is None:
        raise ValueError("press has no configured force limit")
    return check_force_capacity(required_force_mn, force_limit)
