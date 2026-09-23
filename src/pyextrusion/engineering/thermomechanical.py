from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number
from .extrusion_flow import (
    equivalent_extrudate_diameter_mm,
    modified_feltham_mean_strain_rate_s_1,
    sheppard_deformation_semiangle_deg,
)
from .materials import (
    AA6063_SHEPPARD_1999,
    SHEPPARD_1999_TABLE_4_1_AA6063,
    HotWorkingConstitutiveModel,
)
from .metadata import SourceRef
from .pressure import (
    AxisymmetricPressureBreakdown,
    SHEPPARD_1999_EQ_4_3,
    SHEPPARD_1999_EQ_4_4,
    SHEPPARD_1999_EQ_4_5,
    axisymmetric_pressure_breakdown,
    breakthrough_pressure_increment_mpa_from_log_z,
    upset_billet_length_mm,
)
from .rheology import (
    flow_stress_mpa,
    log_zener_hollomon_parameter,
    zener_hollomon_parameter_s_1,
)
from .thermal import (
    SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
    SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES_SOURCE,
    SHEPPARD_1999_STUWE_THERMAL_MODEL,
    StuweSurfaceExitTemperatureEstimate,
    ThermalMaterialProperties,
    stuwe_surface_exit_temperature_estimate,
)

AA6063_DIRECT_OPERATION_MODEL = SourceRef(
    source_kind="derived",
    reference="PyExtrusion AA6063 direct-extrusion single-operation composite model",
    detail=(
        "Composition of validated equivalent-geometry, modified Feltham, "
        "Sheppard-Wright, Sheppard axisymmetric pressure and Stuwe surface "
        "exit-temperature components"
    ),
)

AA6063_DIRECT_OPERATION_LIMITATIONS: tuple[str, ...] = (
    "Single steady operation point for direct extrusion of AA6063.",
    "Uses equivalent axisymmetric geometry; shaped-profile, porthole and bridge-die corrections are not included.",
    "No Integral Profile thermal reconstruction or transient die/container heat-storage model is included.",
    "Flow stress is evaluated at the supplied billet temperature only; temperature-dependent iteration is not performed.",
    "Friction factor is an explicit caller input and is not inferred from alloy, lubricant or tooling condition.",
)


def _positive(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0, exclusive_minimum=True)
    assert result is not None
    return result


def _nonnegative(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0)
    assert result is not None
    return result


def _operation_ratio(extrusion_ratio: float) -> float:
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


def _aa6063_model(model: HotWorkingConstitutiveModel) -> HotWorkingConstitutiveModel:
    if not isinstance(model, HotWorkingConstitutiveModel):
        raise ValueError("constitutive_model must be a HotWorkingConstitutiveModel")
    if model.alloy != "AA6063":
        raise ValueError("this composite operation model is limited to AA6063")
    return model


def _validated_text_items(items: tuple[str, ...], field: str) -> tuple[str, ...]:
    if isinstance(items, (str, bytes)):
        raise ValueError(f"{field} must be a collection of non-empty strings, not a single string")
    values = tuple(items)
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} entries must be non-empty strings")
    return values


@dataclass(frozen=True)
class AA6063DirectExtrusionOperationEstimate:
    """Composed thermomechanical estimate for one AA6063 direct-extrusion point.

    The object deliberately composes existing validated PyExtrusion models. It
    does not introduce porthole/bridge-die corrections, shaped-section pressure
    factors, Integral Profile reconstruction or thermo-mechanical iteration.
    """

    billet_temperature_c: float
    billet_diameter_mm: float
    billet_length_mm: float
    container_diameter_mm: float
    extrusion_ratio: float
    ram_speed_mm_s: float
    friction_factor_m: float
    die_land_length_mm: float
    constitutive_model: HotWorkingConstitutiveModel = AA6063_SHEPPARD_1999
    thermal_properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES
    model_scope: str = "aa6063_equivalent_axisymmetric_direct_extrusion_single_operation_point"
    limitations: tuple[str, ...] = AA6063_DIRECT_OPERATION_LIMITATIONS
    provenance: tuple[SourceRef, ...] = (
        AA6063_DIRECT_OPERATION_MODEL,
        SHEPPARD_1999_TABLE_4_1_AA6063,
        SHEPPARD_1999_EQ_4_3,
        SHEPPARD_1999_EQ_4_4,
        SHEPPARD_1999_EQ_4_5,
        SHEPPARD_1999_STUWE_THERMAL_MODEL,
        SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES_SOURCE,
    )

    def __post_init__(self) -> None:
        billet_temperature = require_number(
            self.billet_temperature_c,
            "billet_temperature_c",
            ValueError,
            minimum=-273.15,
            exclusive_minimum=True,
        )
        billet_diameter = _positive(self.billet_diameter_mm, "billet_diameter_mm")
        billet_length = _positive(self.billet_length_mm, "billet_length_mm")
        container_diameter = _positive(self.container_diameter_mm, "container_diameter_mm")
        ratio = _operation_ratio(self.extrusion_ratio)
        ram_speed = _positive(self.ram_speed_mm_s, "ram_speed_mm_s")
        friction_factor = require_number(
            self.friction_factor_m,
            "friction_factor_m",
            ValueError,
            minimum=0.0,
            maximum=1.0,
        )
        land_length = _nonnegative(self.die_land_length_mm, "die_land_length_mm")
        assert billet_temperature is not None and friction_factor is not None

        if billet_diameter > container_diameter:
            raise ValueError("billet_diameter_mm cannot exceed container_diameter_mm")
        model = _aa6063_model(self.constitutive_model)
        if not isinstance(self.thermal_properties, ThermalMaterialProperties):
            raise ValueError("thermal_properties must be ThermalMaterialProperties")
        if not isinstance(self.model_scope, str) or not self.model_scope.strip():
            raise ValueError("model_scope must be a non-empty string")

        provenance = tuple(self.provenance)
        if any(not isinstance(item, SourceRef) for item in provenance):
            raise ValueError("operation provenance entries must be SourceRef instances")

        object.__setattr__(self, "billet_temperature_c", billet_temperature)
        object.__setattr__(self, "billet_diameter_mm", billet_diameter)
        object.__setattr__(self, "billet_length_mm", billet_length)
        object.__setattr__(self, "container_diameter_mm", container_diameter)
        object.__setattr__(self, "extrusion_ratio", ratio)
        object.__setattr__(self, "ram_speed_mm_s", ram_speed)
        object.__setattr__(self, "friction_factor_m", friction_factor)
        object.__setattr__(self, "die_land_length_mm", land_length)
        object.__setattr__(self, "constitutive_model", model)
        object.__setattr__(self, "model_scope", self.model_scope.strip())
        object.__setattr__(
            self,
            "limitations",
            _validated_text_items(self.limitations, "operation limitations"),
        )
        object.__setattr__(self, "provenance", provenance)

        # Evaluate the coupled pieces once during construction so singular or
        # out-of-scope operation points fail early instead of being hidden in a
        # later property access.
        _ = self.pressure_breakdown
        _ = self.surface_exit_temperature_estimate

    @property
    def equivalent_extrudate_diameter_mm(self) -> float:
        return equivalent_extrudate_diameter_mm(
            self.container_diameter_mm,
            self.extrusion_ratio,
        )

    @property
    def deformation_semiangle_deg(self) -> float:
        return sheppard_deformation_semiangle_deg(self.extrusion_ratio)

    @property
    def exit_speed_m_min(self) -> float:
        value = self.ram_speed_mm_s * self.extrusion_ratio * 60.0 / 1000.0
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("exit speed is outside the representable finite range")
        return value

    @property
    def billet_contact_length_mm(self) -> float:
        return upset_billet_length_mm(
            self.billet_diameter_mm,
            self.billet_length_mm,
            self.container_diameter_mm,
        )

    @property
    def mean_strain_rate_s_1(self) -> float:
        return modified_feltham_mean_strain_rate_s_1(
            self.ram_speed_mm_s,
            self.container_diameter_mm,
            self.extrusion_ratio,
        )

    @property
    def ln_zener_hollomon(self) -> float:
        return log_zener_hollomon_parameter(
            self.mean_strain_rate_s_1,
            self.billet_temperature_c,
            self.constitutive_model,
        )

    @property
    def zener_hollomon_s_1(self) -> float:
        return zener_hollomon_parameter_s_1(
            self.mean_strain_rate_s_1,
            self.billet_temperature_c,
            self.constitutive_model,
        )

    @property
    def flow_stress_mpa(self) -> float:
        return flow_stress_mpa(
            self.mean_strain_rate_s_1,
            self.billet_temperature_c,
            self.constitutive_model,
        )

    @property
    def breakthrough_increment_mpa(self) -> float:
        return breakthrough_pressure_increment_mpa_from_log_z(
            self.ln_zener_hollomon,
            self.constitutive_model,
        )

    @property
    def pressure_breakdown(self) -> AxisymmetricPressureBreakdown:
        return axisymmetric_pressure_breakdown(
            flow_stress_mpa=self.flow_stress_mpa,
            extrusion_ratio=self.extrusion_ratio,
            friction_factor_m=self.friction_factor_m,
            billet_contact_length_mm=self.billet_contact_length_mm,
            container_diameter_mm=self.container_diameter_mm,
            breakthrough_increment_mpa=self.breakthrough_increment_mpa,
        )

    @property
    def surface_exit_temperature_estimate(self) -> StuweSurfaceExitTemperatureEstimate:
        return stuwe_surface_exit_temperature_estimate(
            billet_temperature_c=self.billet_temperature_c,
            flow_stress_mpa=self.flow_stress_mpa,
            extrusion_ratio=self.extrusion_ratio,
            ram_speed_mm_s=self.ram_speed_mm_s,
            billet_contact_length_mm=self.billet_contact_length_mm,
            exit_speed_m_min=self.exit_speed_m_min,
            die_land_length_mm=self.die_land_length_mm,
            properties=self.thermal_properties,
        )

    @property
    def peak_pressure_mpa(self) -> float:
        return self.pressure_breakdown.peak_pressure_mpa

    @property
    def required_force_mn(self) -> float:
        return self.pressure_breakdown.required_force_mn

    @property
    def estimated_surface_exit_temperature_c(self) -> float:
        return self.surface_exit_temperature_estimate.estimated_surface_exit_temperature_c

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        pressure = self.pressure_breakdown
        thermal = self.surface_exit_temperature_estimate
        data.update(
            {
                "equivalent_extrudate_diameter_mm": self.equivalent_extrudate_diameter_mm,
                "deformation_semiangle_deg": self.deformation_semiangle_deg,
                "exit_speed_m_min": self.exit_speed_m_min,
                "billet_contact_length_mm": self.billet_contact_length_mm,
                "mean_strain_rate_s_1": self.mean_strain_rate_s_1,
                "ln_zener_hollomon": self.ln_zener_hollomon,
                "zener_hollomon_s_1": self.zener_hollomon_s_1,
                "flow_stress_mpa": self.flow_stress_mpa,
                "breakthrough_increment_mpa": self.breakthrough_increment_mpa,
                "pressure_breakdown": pressure.to_dict(),
                "surface_exit_temperature_estimate": thermal.to_dict(),
                "peak_pressure_mpa": pressure.peak_pressure_mpa,
                "required_force_mn": pressure.required_force_mn,
                "estimated_surface_exit_temperature_c": (
                    thermal.estimated_surface_exit_temperature_c
                ),
            }
        )
        return data


def aa6063_direct_extrusion_operation_estimate(
    billet_temperature_c: float,
    billet_diameter_mm: float,
    billet_length_mm: float,
    container_diameter_mm: float,
    extrusion_ratio: float,
    ram_speed_mm_s: float,
    friction_factor_m: float,
    die_land_length_mm: float,
    *,
    thermal_properties: ThermalMaterialProperties = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
) -> AA6063DirectExtrusionOperationEstimate:
    """Build the composed AA6063 direct-extrusion thermomechanical estimate."""
    return AA6063DirectExtrusionOperationEstimate(
        billet_temperature_c=billet_temperature_c,
        billet_diameter_mm=billet_diameter_mm,
        billet_length_mm=billet_length_mm,
        container_diameter_mm=container_diameter_mm,
        extrusion_ratio=extrusion_ratio,
        ram_speed_mm_s=ram_speed_mm_s,
        friction_factor_m=friction_factor_m,
        die_land_length_mm=die_land_length_mm,
        thermal_properties=thermal_properties,
    )
