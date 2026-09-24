from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number
from .metadata import SourceRef

SAHA_2000_THERMODYNAMICS_MODEL = SourceRef(
    source_kind="literature",
    reference=(
        "P.K. Saha, Aluminum Extrusion Technology, ASM International, "
        "Chapter 2, Thermodynamics Model, Eq. 1 and Eqs. 8-12"
    ),
    detail=(
        "Transient axisymmetric heat-conduction framework with deformation "
        "and frictional heat-generation source terms"
    ),
)

SAHA_2000_FRICTION_MODEL = SourceRef(
    source_kind="literature",
    reference=(
        "P.K. Saha, Aluminum Extrusion Technology, ASM International, "
        "Chapter 1, friction model, Eqs. 12-15"
    ),
    detail=(
        "Von Mises shear strength and die-material sticking/sliding friction model"
    ),
)

SAHA_AXISYMMETRIC_SEMIDEAD_ZONE_ANGLE_DEG = 45.0
SAHA_MECHANICAL_EQUIVALENT_OF_HEAT_SI = 1.0


def _nonnegative(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0)
    assert result is not None
    return result


def saha_deformation_heat_generation_w_m3(
    flow_stress_mpa: float,
    mean_strain_rate_s_1: float,
) -> float:
    """Return Saha volumetric deformation heat-generation term in W/m3.

    Saha writes the deformation-energy source as U''' = sigma * strain_rate / J.
    In SI, mechanical work and heat are both expressed in joules, so J = 1.

    This function returns the local source term only. It does not solve the
    transient heat equation, apply a heat-partition coefficient or predict an
    exit temperature.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    strain_rate = _nonnegative(mean_strain_rate_s_1, "mean_strain_rate_s_1")

    value = stress_mpa * 1.0e6 * strain_rate / SAHA_MECHANICAL_EQUIVALENT_OF_HEAT_SI
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("deformation heat generation is outside the representable finite range")
    return value


def saha_complete_sticking_shear_stress_mpa(flow_stress_mpa: float) -> float:
    """Return friction shear stress for complete sticking, tau = sigma/sqrt(3).

    Saha uses the Von Mises material shear strength k = sigma/sqrt(3). For
    complete adhesion/sticking at the interface, the friction stress equals k.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    value = stress_mpa / math.sqrt(3.0)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("sticking shear stress is outside the representable finite range")
    return value


def saha_billet_container_heat_flux_w_m2(
    flow_stress_mpa: float,
    ram_speed_mm_s: float,
) -> float:
    """Return Saha billet-container frictional heat flux in W/m2.

    For the source model, shearing is assumed along the billet boundary and
    the interface material speed is taken as the ram speed:

        q_f = sigma * V_R / (sqrt(3) * J)

    The returned quantity is generated interfacial heat flux. This function
    does not decide how that heat is partitioned between billet and container.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    speed_mm_s = _nonnegative(ram_speed_mm_s, "ram_speed_mm_s")

    stress_pa = stress_mpa * 1.0e6
    speed_m_s = speed_mm_s / 1000.0
    value = (
        stress_pa
        * speed_m_s
        / (math.sqrt(3.0) * SAHA_MECHANICAL_EQUIVALENT_OF_HEAT_SI)
    )
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("billet-container heat flux is outside the representable finite range")
    return value


def saha_dead_metal_zone_material_speed_mm_s(ram_speed_mm_s: float) -> float:
    """Return Saha approximate flowing-metal speed at the DMZ interface.

    The finite-difference model described in the book assumes a straight conical
    dead-metal-zone surface with semiangle alpha = 45 degrees and uses

        V_mj = V_R / cos(alpha)

    No alternate semiangle is accepted here because doing so would no longer be
    the source-exact Saha assumption.
    """
    speed_mm_s = _nonnegative(ram_speed_mm_s, "ram_speed_mm_s")
    value = speed_mm_s / math.cos(math.radians(SAHA_AXISYMMETRIC_SEMIDEAD_ZONE_ANGLE_DEG))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("dead-metal-zone material speed is outside the representable finite range")
    return value


def saha_dead_metal_zone_heat_flux_w_m2(
    flow_stress_mpa: float,
    ram_speed_mm_s: float,
) -> float:
    """Return Saha dead-metal-zone/flowing-metal heat flux in W/m2.

        q_f = sigma * V_mj / (sqrt(3) * J)
        V_mj = V_R / cos(45 deg)

    The returned quantity is a generated interfacial heat flux only.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    material_speed_mm_s = saha_dead_metal_zone_material_speed_mm_s(ram_speed_mm_s)

    stress_pa = stress_mpa * 1.0e6
    speed_m_s = material_speed_mm_s / 1000.0
    value = (
        stress_pa
        * speed_m_s
        / (math.sqrt(3.0) * SAHA_MECHANICAL_EQUIVALENT_OF_HEAT_SI)
    )
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("dead-metal-zone heat flux is outside the representable finite range")
    return value


def saha_die_bearing_heat_flux_w_m2(
    friction_stress_mpa: float,
    exit_speed_m_min: float,
) -> float:
    """Return Saha die-bearing/material frictional heat flux in W/m2.

        q_f = tau_f * V_E / J

    friction_stress_mpa is explicit because Saha allows the bearing friction
    state to vary between sticking and sliding. Use
    saha_complete_sticking_shear_stress_mpa when complete sticking is the
    declared interface condition.
    """
    friction_mpa = _nonnegative(friction_stress_mpa, "friction_stress_mpa")
    speed_m_min = _nonnegative(exit_speed_m_min, "exit_speed_m_min")

    friction_pa = friction_mpa * 1.0e6
    speed_m_s = speed_m_min / 60.0
    value = friction_pa * speed_m_s / SAHA_MECHANICAL_EQUIVALENT_OF_HEAT_SI
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("die-bearing heat flux is outside the representable finite range")
    return value


def saha_complete_sticking_die_bearing_heat_flux_w_m2(
    flow_stress_mpa: float,
    exit_speed_m_min: float,
) -> float:
    """Return Saha die-bearing heat flux for complete sticking."""
    friction_stress = saha_complete_sticking_shear_stress_mpa(flow_stress_mpa)
    return saha_die_bearing_heat_flux_w_m2(friction_stress, exit_speed_m_min)


@dataclass(frozen=True)
class SahaThermalSourceTerms:
    """Local Saha thermal source terms without a transient temperature solver.

    This object bundles independently evaluable source terms only. It does not
    contain geometry integration, heat partition, boundary conditions, tooling
    temperatures, porthole corrections or an exit-temperature prediction.
    """

    flow_stress_mpa: float
    mean_strain_rate_s_1: float
    ram_speed_mm_s: float
    exit_speed_m_min: float
    bearing_friction_stress_mpa: float
    model_scope: str = "saha_local_thermal_source_terms_only"
    provenance: tuple[SourceRef, ...] = (
        SAHA_2000_THERMODYNAMICS_MODEL,
        SAHA_2000_FRICTION_MODEL,
    )

    def __post_init__(self) -> None:
        flow_stress = _nonnegative(self.flow_stress_mpa, "flow_stress_mpa")
        strain_rate = _nonnegative(self.mean_strain_rate_s_1, "mean_strain_rate_s_1")
        ram_speed = _nonnegative(self.ram_speed_mm_s, "ram_speed_mm_s")
        exit_speed = _nonnegative(self.exit_speed_m_min, "exit_speed_m_min")
        bearing_stress = _nonnegative(
            self.bearing_friction_stress_mpa,
            "bearing_friction_stress_mpa",
        )

        if not isinstance(self.model_scope, str) or not self.model_scope.strip():
            raise ValueError("model_scope must be a non-empty string")

        provenance = tuple(self.provenance)
        if any(not isinstance(item, SourceRef) for item in provenance):
            raise ValueError("Saha thermal-source provenance entries must be SourceRef instances")

        object.__setattr__(self, "flow_stress_mpa", flow_stress)
        object.__setattr__(self, "mean_strain_rate_s_1", strain_rate)
        object.__setattr__(self, "ram_speed_mm_s", ram_speed)
        object.__setattr__(self, "exit_speed_m_min", exit_speed)
        object.__setattr__(self, "bearing_friction_stress_mpa", bearing_stress)
        object.__setattr__(self, "model_scope", self.model_scope.strip())
        object.__setattr__(self, "provenance", provenance)

    @property
    def deformation_heat_generation_w_m3(self) -> float:
        return saha_deformation_heat_generation_w_m3(
            self.flow_stress_mpa,
            self.mean_strain_rate_s_1,
        )

    @property
    def billet_container_heat_flux_w_m2(self) -> float:
        return saha_billet_container_heat_flux_w_m2(
            self.flow_stress_mpa,
            self.ram_speed_mm_s,
        )

    @property
    def dead_metal_zone_material_speed_mm_s(self) -> float:
        return saha_dead_metal_zone_material_speed_mm_s(self.ram_speed_mm_s)

    @property
    def dead_metal_zone_heat_flux_w_m2(self) -> float:
        return saha_dead_metal_zone_heat_flux_w_m2(
            self.flow_stress_mpa,
            self.ram_speed_mm_s,
        )

    @property
    def die_bearing_heat_flux_w_m2(self) -> float:
        return saha_die_bearing_heat_flux_w_m2(
            self.bearing_friction_stress_mpa,
            self.exit_speed_m_min,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "deformation_heat_generation_w_m3": self.deformation_heat_generation_w_m3,
                "billet_container_heat_flux_w_m2": self.billet_container_heat_flux_w_m2,
                "dead_metal_zone_material_speed_mm_s": self.dead_metal_zone_material_speed_mm_s,
                "dead_metal_zone_heat_flux_w_m2": self.dead_metal_zone_heat_flux_w_m2,
                "die_bearing_heat_flux_w_m2": self.die_bearing_heat_flux_w_m2,
            }
        )
        return data


def saha_complete_sticking_thermal_source_terms(
    flow_stress_mpa: float,
    mean_strain_rate_s_1: float,
    ram_speed_mm_s: float,
    exit_speed_m_min: float,
) -> SahaThermalSourceTerms:
    """Build Saha source terms with complete sticking at the die bearing."""
    return SahaThermalSourceTerms(
        flow_stress_mpa=flow_stress_mpa,
        mean_strain_rate_s_1=mean_strain_rate_s_1,
        ram_speed_mm_s=ram_speed_mm_s,
        exit_speed_m_min=exit_speed_m_min,
        bearing_friction_stress_mpa=saha_complete_sticking_shear_stress_mpa(flow_stress_mpa),
    )
