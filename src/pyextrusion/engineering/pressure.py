from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number
from .materials import HotWorkingConstitutiveModel
from .metadata import Interval, SourceRef
from .mechanics import circular_area_m2_from_diameter_mm, force_mn_from_specific_pressure_mpa

SHEPPARD_1999_EQ_4_3 = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), Eq. 4.3",
    detail="axisymmetric steady-state rod-extrusion pressure regression",
)

SHEPPARD_1999_EQ_4_4 = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), Eq. 4.4",
    detail="direct-extrusion container-friction extension",
)

SHEPPARD_1999_EQ_4_5 = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), Eq. 4.5",
    detail="incremental pressure correlation for breakthrough",
)

SHEPPARD_STICKING_FRICTION_FACTOR_RANGE = Interval(0.8, 0.9)


def _positive(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0, exclusive_minimum=True)
    assert result is not None
    return result


def _nonnegative(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0)
    assert result is not None
    return result


def _pressure_model_ratio(extrusion_ratio: float) -> float:
    ratio = require_number(
        extrusion_ratio,
        "extrusion_ratio",
        ValueError,
        minimum=1.0,
        maximum=100.0,
        exclusive_minimum=True,
    )
    assert ratio is not None
    return ratio


def upset_billet_length_mm(
    billet_diameter_mm: float,
    billet_length_mm: float,
    container_diameter_mm: float,
) -> float:
    """Return billet length after ideal upset to the container bore.

    Uses volume conservation for a cylindrical billet:

        L_upset = L_initial (D_billet / D_container)^2

    The helper models geometry only. It does not include butt loss, elastic
    deformation, flash, trapped air, taper or local non-uniform upsetting.
    """
    billet_diameter = _positive(billet_diameter_mm, "billet_diameter_mm")
    billet_length = _positive(billet_length_mm, "billet_length_mm")
    container_diameter = _positive(container_diameter_mm, "container_diameter_mm")
    if billet_diameter > container_diameter:
        raise ValueError("billet_diameter_mm cannot exceed container_diameter_mm")

    value = billet_length * (billet_diameter / container_diameter) ** 2
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("upset billet length is outside the representable finite range")
    return value


def axisymmetric_steady_deformation_pressure_mpa(
    flow_stress_mpa: float,
    extrusion_ratio: float,
) -> float:
    """Return Sheppard Eq. 4.3 steady-state pressure for rod extrusion.

    The correlation is p = sigma (0.171 + 1.8594 ln R).

    Sheppard states that this regression is valid for rod extrusion up to an
    extrusion ratio of 100. PyExtrusion therefore rejects R > 100 rather than
    extrapolating silently.
    """
    stress = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    ratio = _pressure_model_ratio(extrusion_ratio)

    value = stress * (0.171 + 1.8594 * math.log(ratio))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("steady deformation pressure is outside the representable finite range")
    return value


def container_friction_pressure_increment_mpa(
    flow_stress_mpa: float,
    friction_factor_m: float,
    billet_contact_length_mm: float,
    container_diameter_mm: float,
) -> float:
    """Return the container-friction contribution in Sheppard Eq. 4.4.

    The increment is

        sigma * 4 m L / (sqrt(3) D_B)

    where L is the billet length in contact with the container after upsetting
    and D_B is the filled billet/container diameter.

    The friction factor is an explicit caller input. Sheppard reports values
    around 0.8-0.9 for conditions close to sticking, but PyExtrusion does not
    silently substitute a default.
    """
    stress = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    friction_factor = require_number(
        friction_factor_m,
        "friction_factor_m",
        ValueError,
        minimum=0.0,
        maximum=1.0,
    )
    contact_length = _nonnegative(billet_contact_length_mm, "billet_contact_length_mm")
    diameter = _positive(container_diameter_mm, "container_diameter_mm")
    assert friction_factor is not None

    value = stress * 4.0 * friction_factor * contact_length / (math.sqrt(3.0) * diameter)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("container friction pressure is outside the representable finite range")
    return value


def axisymmetric_steady_pressure_mpa(
    flow_stress_mpa: float,
    extrusion_ratio: float,
    friction_factor_m: float,
    billet_contact_length_mm: float,
    container_diameter_mm: float,
) -> float:
    """Return axisymmetric steady direct-extrusion pressure including container friction."""
    base = axisymmetric_steady_deformation_pressure_mpa(flow_stress_mpa, extrusion_ratio)
    friction = container_friction_pressure_increment_mpa(
        flow_stress_mpa,
        friction_factor_m,
        billet_contact_length_mm,
        container_diameter_mm,
    )
    value = base + friction
    if not math.isfinite(value):
        raise ValueError("axisymmetric steady pressure is outside the representable finite range")
    return value


def breakthrough_pressure_increment_mpa_from_log_z(
    ln_z: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return Sheppard Eq. 4.5 breakthrough-pressure increment in MPa.

    The empirical correlation is

        delta_p = 6.62 + 0.921 * ln(Z/A) / (alpha n)

    with alpha in MPa^-1.

    The function returns the correlation result without clipping. A non-positive
    result indicates that the supplied state is outside the physically useful
    range of the correlation and should not be interpreted as a negative
    breakthrough requirement.
    """
    if not isinstance(model, HotWorkingConstitutiveModel):
        raise ValueError("model must be a HotWorkingConstitutiveModel")
    log_z = require_number(ln_z, "ln_z", ValueError)
    assert log_z is not None

    value = 6.62 + 0.921 * (log_z - model.ln_A) / (model.alpha_mpa_inv * model.n)
    if not math.isfinite(value):
        raise ValueError("breakthrough pressure increment is outside the representable finite range")
    return value


def breakthrough_pressure_increment_mpa(
    zener_hollomon_s_1: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return Sheppard Eq. 4.5 breakthrough-pressure increment from Z."""
    z_value = _positive(zener_hollomon_s_1, "zener_hollomon_s_1")
    return breakthrough_pressure_increment_mpa_from_log_z(math.log(z_value), model)


@dataclass(frozen=True)
class AxisymmetricPressureBreakdown:
    """Traceable axisymmetric direct-extrusion pressure decomposition.

    This result represents the rod/equivalent-axisymmetric model only. It is not
    a porthole-die, bridge-die or shaped-section correction model.
    """

    flow_stress_mpa: float
    extrusion_ratio: float
    friction_factor_m: float
    billet_contact_length_mm: float
    container_diameter_mm: float
    deformation_pressure_mpa: float
    container_friction_pressure_mpa: float
    breakthrough_increment_mpa: float
    peak_pressure_mpa: float
    required_force_mn: float
    model_scope: str = "axisymmetric_equivalent_direct_extrusion"
    provenance: tuple[SourceRef, ...] = (
        SHEPPARD_1999_EQ_4_3,
        SHEPPARD_1999_EQ_4_4,
        SHEPPARD_1999_EQ_4_5,
    )

    def __post_init__(self) -> None:
        for field, value in (
            ("flow_stress_mpa", self.flow_stress_mpa),
            ("extrusion_ratio", self.extrusion_ratio),
            ("friction_factor_m", self.friction_factor_m),
            ("billet_contact_length_mm", self.billet_contact_length_mm),
            ("container_diameter_mm", self.container_diameter_mm),
            ("deformation_pressure_mpa", self.deformation_pressure_mpa),
            ("container_friction_pressure_mpa", self.container_friction_pressure_mpa),
            ("peak_pressure_mpa", self.peak_pressure_mpa),
            ("required_force_mn", self.required_force_mn),
        ):
            number = require_number(value, field, ValueError, minimum=0.0)
            assert number is not None
            object.__setattr__(self, field, number)

        increment = require_number(self.breakthrough_increment_mpa, "breakthrough_increment_mpa", ValueError)
        assert increment is not None
        object.__setattr__(self, "breakthrough_increment_mpa", increment)

        if not isinstance(self.model_scope, str) or not self.model_scope.strip():
            raise ValueError("model_scope must be a non-empty string")
        object.__setattr__(self, "model_scope", self.model_scope.strip())

        provenance = tuple(self.provenance)
        if any(not isinstance(item, SourceRef) for item in provenance):
            raise ValueError("pressure provenance entries must be SourceRef instances")
        object.__setattr__(self, "provenance", provenance)

    @property
    def steady_pressure_mpa(self) -> float:
        return self.deformation_pressure_mpa + self.container_friction_pressure_mpa

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steady_pressure_mpa"] = self.steady_pressure_mpa
        return data


def axisymmetric_pressure_breakdown(
    flow_stress_mpa: float,
    extrusion_ratio: float,
    friction_factor_m: float,
    billet_contact_length_mm: float,
    container_diameter_mm: float,
    breakthrough_increment_mpa: float,
) -> AxisymmetricPressureBreakdown:
    """Compose the axisymmetric pressure model and convert peak pressure to force."""
    deformation = axisymmetric_steady_deformation_pressure_mpa(flow_stress_mpa, extrusion_ratio)
    friction = container_friction_pressure_increment_mpa(
        flow_stress_mpa,
        friction_factor_m,
        billet_contact_length_mm,
        container_diameter_mm,
    )
    increment = require_number(breakthrough_increment_mpa, "breakthrough_increment_mpa", ValueError)
    assert increment is not None

    peak = deformation + friction + increment
    if not math.isfinite(peak) or peak < 0.0:
        raise ValueError("peak pressure must be non-negative and finite")

    area_m2 = circular_area_m2_from_diameter_mm(container_diameter_mm)
    required_force = force_mn_from_specific_pressure_mpa(peak, area_m2)

    return AxisymmetricPressureBreakdown(
        flow_stress_mpa=flow_stress_mpa,
        extrusion_ratio=extrusion_ratio,
        friction_factor_m=friction_factor_m,
        billet_contact_length_mm=billet_contact_length_mm,
        container_diameter_mm=container_diameter_mm,
        deformation_pressure_mpa=deformation,
        container_friction_pressure_mpa=friction,
        breakthrough_increment_mpa=increment,
        peak_pressure_mpa=peak,
        required_force_mn=required_force,
    )
