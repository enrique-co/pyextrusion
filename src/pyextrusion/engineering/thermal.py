from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number
from .metadata import SourceRef

SHEPPARD_1999_STUWE_THERMAL_MODEL = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), section 2.5.2, pp. 50-51",
    detail=(
        "Three-component approximate temperature-rise model reproduced by Sheppard "
        "from H.P. Stuwe (1968), Metall. 22, 1197"
    ),
)

SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES_SOURCE = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), section 2.5.4, p. 56",
    detail="Constant thermal properties stated for aluminium alloys in the integral-profile discussion",
)

SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES_SOURCE = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), section 2.5.4, pp. 56-57",
    detail="Constant thermal properties stated for normal Cr-V extrusion tooling steels",
)

SHEPPARD_1999_INTERFACE_TEMPERATURE_EQ_2_25 = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), Eq. 2.25, p. 56",
    detail=(
        "Billet/tooling interface temperature from Fourier heat flow with linear "
        "subcutaneous temperature distributions"
    ),
)


def _positive(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0, exclusive_minimum=True)
    assert result is not None
    return result


def _nonnegative(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0)
    assert result is not None
    return result


@dataclass(frozen=True)
class ThermalMaterialProperties:
    """Constant thermal properties for one material model.

    These are scalar properties, not temperature-dependent functions. PyExtrusion
    does not infer temperature dependence or alloy-specific corrections.
    """

    thermal_conductivity_w_m_k: float
    density_kg_m3: float
    specific_heat_j_kg_k: float
    provenance: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        conductivity = _positive(self.thermal_conductivity_w_m_k, "thermal_conductivity_w_m_k")
        density = _positive(self.density_kg_m3, "density_kg_m3")
        specific_heat = _positive(self.specific_heat_j_kg_k, "specific_heat_j_kg_k")
        provenance = tuple(self.provenance)
        if any(not isinstance(item, SourceRef) for item in provenance):
            raise ValueError("thermal-property provenance entries must be SourceRef instances")

        object.__setattr__(self, "thermal_conductivity_w_m_k", conductivity)
        object.__setattr__(self, "density_kg_m3", density)
        object.__setattr__(self, "specific_heat_j_kg_k", specific_heat)
        object.__setattr__(self, "provenance", provenance)

    @property
    def thermal_diffusivity_m2_s(self) -> float:
        """Return thermal diffusivity a = k / (rho Cp) in m2/s."""
        value = self.thermal_conductivity_w_m_k / (
            self.density_kg_m3 * self.specific_heat_j_kg_k
        )
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("thermal diffusivity is outside the representable finite range")
        return value

    @property
    def thermal_effusivity_w_sqrt_s_m2_k(self) -> float:
        """Return thermal effusivity sqrt(k rho Cp).

        Unit: W*sqrt(s)/(m2*K).
        """
        value = math.sqrt(
            self.thermal_conductivity_w_m_k
            * self.density_kg_m3
            * self.specific_heat_j_kg_k
        )
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("thermal effusivity is outside the representable finite range")
        return value

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["thermal_diffusivity_m2_s"] = self.thermal_diffusivity_m2_s
        data["thermal_effusivity_w_sqrt_s_m2_k"] = self.thermal_effusivity_w_sqrt_s_m2_k
        return data


SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES = ThermalMaterialProperties(
    thermal_conductivity_w_m_k=201.0,
    density_kg_m3=2800.0,
    specific_heat_j_kg_k=1063.9,
    provenance=(SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES_SOURCE,),
)

SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES = ThermalMaterialProperties(
    thermal_conductivity_w_m_k=32.65,
    density_kg_m3=7860.0,
    specific_heat_j_kg_k=489.76,
    provenance=(SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES_SOURCE,),
)


def sheppard_billet_container_interface_temperature_c(
    billet_temperature_c: float,
    container_temperature_c: float,
    billet_properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
    container_properties: ThermalMaterialProperties = SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES,
) -> float:
    """Return Sheppard Eq. 2.25 billet/container interface temperature.

    Sheppard writes

        (T_B - T_i) / (T_i - T_C)
            = sqrt(k_C rho_C Cp_C / (k_B rho_B Cp_B))

    after assuming linear temperature distributions in the subcutaneous layers
    and Fourier heat flow. This is an interface-temperature relation only. It
    does not calculate frictional heat partition, transient heat flux or a
    complete billet/container thermal history.
    """
    billet_temperature = require_number(
        billet_temperature_c,
        "billet_temperature_c",
        ValueError,
        minimum=-273.15,
        exclusive_minimum=True,
    )
    container_temperature = require_number(
        container_temperature_c,
        "container_temperature_c",
        ValueError,
        minimum=-273.15,
        exclusive_minimum=True,
    )
    assert billet_temperature is not None and container_temperature is not None

    if not isinstance(billet_properties, ThermalMaterialProperties):
        raise ValueError("billet_properties must be ThermalMaterialProperties")
    if not isinstance(container_properties, ThermalMaterialProperties):
        raise ValueError("container_properties must be ThermalMaterialProperties")

    ratio = (
        container_properties.thermal_effusivity_w_sqrt_s_m2_k
        / billet_properties.thermal_effusivity_w_sqrt_s_m2_k
    )
    value = (billet_temperature + ratio * container_temperature) / (1.0 + ratio)
    if not math.isfinite(value):
        raise ValueError("interface temperature is outside the representable finite range")
    return value


def stuwe_deformation_temperature_rise_c(
    flow_stress_mpa: float,
    extrusion_ratio: float,
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> float:
    """Return Stuwe deformation temperature rise, Delta T1, in degC.

    Sheppard reproduces the approximation:

        Delta T1 = sigma_bar ln(R) / (sqrt(3) rho Cp)

    and describes it as the nearly adiabatic conversion of deformation work into
    heat. flow_stress_mpa is converted to pascals internally.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    ratio = require_number(
        extrusion_ratio,
        "extrusion_ratio",
        ValueError,
        minimum=1.0,
        exclusive_minimum=True,
    )
    if not isinstance(properties, ThermalMaterialProperties):
        raise ValueError("properties must be ThermalMaterialProperties")
    assert ratio is not None

    stress_pa = stress_mpa * 1.0e6
    volumetric_heat_capacity = properties.density_kg_m3 * properties.specific_heat_j_kg_k
    value = stress_pa * math.log(ratio) / (math.sqrt(3.0) * volumetric_heat_capacity)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("deformation temperature rise is outside the representable finite range")
    return value


def stuwe_container_wall_temperature_rise_c(
    flow_stress_mpa: float,
    ram_speed_mm_s: float,
    billet_contact_length_mm: float,
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> float:
    """Return Stuwe billet-surface temperature rise, Delta T2, in degC.

    Sheppard reproduces:

        Delta T2 = sigma_bar / (4 sqrt(3) rho Cp)
                   * sqrt(V_R L_B / a)

    where a is thermal diffusivity. The equation contains no explicit
    friction-factor input; PyExtrusion therefore does not inject one.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    speed_mm_s = _nonnegative(ram_speed_mm_s, "ram_speed_mm_s")
    contact_length_mm = _nonnegative(billet_contact_length_mm, "billet_contact_length_mm")
    if not isinstance(properties, ThermalMaterialProperties):
        raise ValueError("properties must be ThermalMaterialProperties")

    stress_pa = stress_mpa * 1.0e6
    speed_m_s = speed_mm_s / 1000.0
    length_m = contact_length_mm / 1000.0
    volumetric_heat_capacity = properties.density_kg_m3 * properties.specific_heat_j_kg_k
    value = (
        stress_pa
        / (4.0 * math.sqrt(3.0) * volumetric_heat_capacity)
        * math.sqrt(speed_m_s * length_m / properties.thermal_diffusivity_m2_s)
    )
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("container-wall temperature rise is outside the representable finite range")
    return value


def stuwe_container_heating_depth_mm(
    ram_speed_mm_s: float,
    billet_contact_length_mm: float,
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> float:
    """Return Stuwe container-friction heating depth y in millimetres.

        y ~= sqrt(a L_B / V_R)

    A positive ram speed is required because the source expression is singular at
    zero speed.
    """
    speed_mm_s = _positive(ram_speed_mm_s, "ram_speed_mm_s")
    contact_length_mm = _nonnegative(billet_contact_length_mm, "billet_contact_length_mm")
    if not isinstance(properties, ThermalMaterialProperties):
        raise ValueError("properties must be ThermalMaterialProperties")

    speed_m_s = speed_mm_s / 1000.0
    length_m = contact_length_mm / 1000.0
    depth_m = math.sqrt(properties.thermal_diffusivity_m2_s * length_m / speed_m_s)
    if not math.isfinite(depth_m) or depth_m < 0.0:
        raise ValueError("container heating depth is outside the representable finite range")
    return depth_m * 1000.0


def stuwe_die_land_temperature_rise_c(
    flow_stress_mpa: float,
    exit_speed_m_min: float,
    die_land_length_mm: float,
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> float:
    """Return Stuwe extrudate-surface die-land temperature rise, Delta T3, in degC.

    Sheppard reproduces:

        Delta T3 = sigma_bar / (4 sqrt(3) rho Cp)
                   * sqrt(V_E L_D / a)

    where V_E is exit speed and L_D is die-land length.
    """
    stress_mpa = _nonnegative(flow_stress_mpa, "flow_stress_mpa")
    speed_m_min = _nonnegative(exit_speed_m_min, "exit_speed_m_min")
    land_length_mm = _nonnegative(die_land_length_mm, "die_land_length_mm")
    if not isinstance(properties, ThermalMaterialProperties):
        raise ValueError("properties must be ThermalMaterialProperties")

    stress_pa = stress_mpa * 1.0e6
    speed_m_s = speed_m_min / 60.0
    length_m = land_length_mm / 1000.0
    volumetric_heat_capacity = properties.density_kg_m3 * properties.specific_heat_j_kg_k
    value = (
        stress_pa
        / (4.0 * math.sqrt(3.0) * volumetric_heat_capacity)
        * math.sqrt(speed_m_s * length_m / properties.thermal_diffusivity_m2_s)
    )
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("die-land temperature rise is outside the representable finite range")
    return value


def stuwe_die_land_heating_depth_mm(
    exit_speed_m_min: float,
    die_land_length_mm: float,
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> float:
    """Return Stuwe die-land heating depth y_D in millimetres.

        y_D = sqrt(a L_D / V_E)

    A positive exit speed is required because the source expression is singular
    at zero speed.
    """
    speed_m_min = _positive(exit_speed_m_min, "exit_speed_m_min")
    land_length_mm = _nonnegative(die_land_length_mm, "die_land_length_mm")
    if not isinstance(properties, ThermalMaterialProperties):
        raise ValueError("properties must be ThermalMaterialProperties")

    speed_m_s = speed_m_min / 60.0
    length_m = land_length_mm / 1000.0
    depth_m = math.sqrt(properties.thermal_diffusivity_m2_s * length_m / speed_m_s)
    if not math.isfinite(depth_m) or depth_m < 0.0:
        raise ValueError("die-land heating depth is outside the representable finite range")
    return depth_m * 1000.0


@dataclass(frozen=True)
class StuweSurfaceExitTemperatureEstimate:
    """Three-component Stuwe estimate of emerging-extrusion surface temperature.

    The estimate sums the deformation, container-wall and die-land temperature
    rises reproduced by Sheppard. It is deliberately labelled a surface estimate:
    the second and third source equations are surface-layer temperature rises.

    The model does not explicitly include container temperature, die temperature,
    ram/dummy-block conduction, transient tooling heat storage, porthole geometry
    or a temperature-dependent property law.
    """

    billet_temperature_c: float
    flow_stress_mpa: float
    extrusion_ratio: float
    ram_speed_mm_s: float
    billet_contact_length_mm: float
    exit_speed_m_min: float
    die_land_length_mm: float
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES
    model_scope: str = "stuwe_three_component_surface_exit_estimate"
    provenance: tuple[SourceRef, ...] = (SHEPPARD_1999_STUWE_THERMAL_MODEL,)

    def __post_init__(self) -> None:
        billet_temperature = require_number(
            self.billet_temperature_c,
            "billet_temperature_c",
            ValueError,
            minimum=-273.15,
            exclusive_minimum=True,
        )
        flow_stress = _nonnegative(self.flow_stress_mpa, "flow_stress_mpa")
        ratio = require_number(
            self.extrusion_ratio,
            "extrusion_ratio",
            ValueError,
            minimum=1.0,
            exclusive_minimum=True,
        )
        ram_speed = _positive(self.ram_speed_mm_s, "ram_speed_mm_s")
        contact_length = _nonnegative(self.billet_contact_length_mm, "billet_contact_length_mm")
        exit_speed = _positive(self.exit_speed_m_min, "exit_speed_m_min")
        land_length = _nonnegative(self.die_land_length_mm, "die_land_length_mm")
        assert billet_temperature is not None and ratio is not None

        if not isinstance(self.properties, ThermalMaterialProperties):
            raise ValueError("properties must be ThermalMaterialProperties")
        if not isinstance(self.model_scope, str) or not self.model_scope.strip():
            raise ValueError("model_scope must be a non-empty string")

        provenance = tuple(self.provenance)
        if any(not isinstance(item, SourceRef) for item in provenance):
            raise ValueError("thermal-estimate provenance entries must be SourceRef instances")

        object.__setattr__(self, "billet_temperature_c", billet_temperature)
        object.__setattr__(self, "flow_stress_mpa", flow_stress)
        object.__setattr__(self, "extrusion_ratio", ratio)
        object.__setattr__(self, "ram_speed_mm_s", ram_speed)
        object.__setattr__(self, "billet_contact_length_mm", contact_length)
        object.__setattr__(self, "exit_speed_m_min", exit_speed)
        object.__setattr__(self, "die_land_length_mm", land_length)
        object.__setattr__(self, "model_scope", self.model_scope.strip())
        object.__setattr__(self, "provenance", provenance)

    @property
    def deformation_temperature_rise_c(self) -> float:
        return stuwe_deformation_temperature_rise_c(
            self.flow_stress_mpa,
            self.extrusion_ratio,
            self.properties,
        )

    @property
    def container_wall_temperature_rise_c(self) -> float:
        return stuwe_container_wall_temperature_rise_c(
            self.flow_stress_mpa,
            self.ram_speed_mm_s,
            self.billet_contact_length_mm,
            self.properties,
        )

    @property
    def die_land_temperature_rise_c(self) -> float:
        return stuwe_die_land_temperature_rise_c(
            self.flow_stress_mpa,
            self.exit_speed_m_min,
            self.die_land_length_mm,
            self.properties,
        )

    @property
    def total_temperature_rise_c(self) -> float:
        return (
            self.deformation_temperature_rise_c
            + self.container_wall_temperature_rise_c
            + self.die_land_temperature_rise_c
        )

    @property
    def estimated_surface_exit_temperature_c(self) -> float:
        return self.billet_temperature_c + self.total_temperature_rise_c

    @property
    def container_heating_depth_mm(self) -> float:
        return stuwe_container_heating_depth_mm(
            self.ram_speed_mm_s,
            self.billet_contact_length_mm,
            self.properties,
        )

    @property
    def die_land_heating_depth_mm(self) -> float:
        return stuwe_die_land_heating_depth_mm(
            self.exit_speed_m_min,
            self.die_land_length_mm,
            self.properties,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "thermal_diffusivity_m2_s": self.properties.thermal_diffusivity_m2_s,
                "deformation_temperature_rise_c": self.deformation_temperature_rise_c,
                "container_wall_temperature_rise_c": self.container_wall_temperature_rise_c,
                "die_land_temperature_rise_c": self.die_land_temperature_rise_c,
                "total_temperature_rise_c": self.total_temperature_rise_c,
                "estimated_surface_exit_temperature_c": self.estimated_surface_exit_temperature_c,
                "container_heating_depth_mm": self.container_heating_depth_mm,
                "die_land_heating_depth_mm": self.die_land_heating_depth_mm,
            }
        )
        return data


def stuwe_surface_exit_temperature_estimate(
    billet_temperature_c: float,
    flow_stress_mpa: float,
    extrusion_ratio: float,
    ram_speed_mm_s: float,
    billet_contact_length_mm: float,
    exit_speed_m_min: float,
    die_land_length_mm: float,
    properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> StuweSurfaceExitTemperatureEstimate:
    """Build a non-contradictory Stuwe three-component surface estimate."""
    return StuweSurfaceExitTemperatureEstimate(
        billet_temperature_c=billet_temperature_c,
        flow_stress_mpa=flow_stress_mpa,
        extrusion_ratio=extrusion_ratio,
        ram_speed_mm_s=ram_speed_mm_s,
        billet_contact_length_mm=billet_contact_length_mm,
        exit_speed_m_min=exit_speed_m_min,
        die_land_length_mm=die_land_length_mm,
        properties=properties,
    )
