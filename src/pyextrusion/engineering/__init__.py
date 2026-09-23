"""Engineering foundations for advanced PyExtrusion models.

This package contains press-independent equations and traceability models.
Press-specific limits, hydraulic layouts and plant data must be supplied as
configuration rather than embedded in these equations.
"""

from .extrusion_flow import (
    equivalent_extrudate_diameter_mm,
    modified_feltham_mean_strain_rate_s_1,
    sheppard_deformation_semiangle_deg,
)
from .materials import (
    AA6063_SHEPPARD_1999,
    SHEPPARD_1999_TABLE_4_1_AA6063,
    UNIVERSAL_GAS_CONSTANT_J_MOL_K,
    HotWorkingConstitutiveModel,
)
from .metadata import Confidence, EngineeringResult, EstimateKind, Interval, SourceKind, SourceRef
from .mechanics import (
    circular_area_m2_from_diameter_mm,
    flow_l_min_from_area_m2_speed_mm_s,
    force_mn_from_specific_pressure_mpa,
    hydraulic_force_contribution_mn_from_pressure_bar,
    hydraulic_pressure_bar_from_force_contribution_mn,
    specific_pressure_mpa_from_force_mn,
    true_strain_from_extrusion_ratio,
)
from .power import (
    EnergyComparison,
    SpecificEnergyBasis,
    compare_specific_energy_kwh_per_tonne,
    energy_kwh_from_constant_power_kw,
    hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min,
    ram_power_kw_from_force_mn_speed_mm_s,
    ram_work_kwh_from_constant_force_mn_stroke_mm,
    specific_energy_kwh_per_tonne,
)
from .pressure import (
    AxisymmetricPressureBreakdown,
    SHEPPARD_1999_EQ_4_3,
    SHEPPARD_1999_EQ_4_4,
    SHEPPARD_1999_EQ_4_5,
    SHEPPARD_STICKING_FRICTION_FACTOR_RANGE,
    axisymmetric_pressure_breakdown,
    axisymmetric_steady_deformation_pressure_mpa,
    axisymmetric_steady_pressure_mpa,
    breakthrough_pressure_increment_mpa,
    breakthrough_pressure_increment_mpa_from_log_z,
    container_friction_pressure_increment_mpa,
    upset_billet_length_mm,
)
from .press import (
    ForceCapacityCheck,
    ForceLimitSource,
    HydraulicSystemSpec,
    InstalledPowerKind,
    PressEngineeringSpec,
    RamOperatingRange,
    check_force_capacity,
    check_press_force_capacity,
)
from .rheology import (
    flow_stress_mpa,
    log_zener_hollomon_parameter,
    steady_state_flow_stress_mpa,
    steady_state_flow_stress_mpa_from_log_z,
    zener_hollomon_parameter_s_1,
)

__all__ = [
    "AA6063_SHEPPARD_1999",
    "AxisymmetricPressureBreakdown",
    "Confidence",
    "EnergyComparison",
    "EngineeringResult",
    "EstimateKind",
    "ForceCapacityCheck",
    "ForceLimitSource",
    "HotWorkingConstitutiveModel",
    "HydraulicSystemSpec",
    "InstalledPowerKind",
    "Interval",
    "PressEngineeringSpec",
    "RamOperatingRange",
    "SHEPPARD_1999_EQ_4_3",
    "SHEPPARD_1999_EQ_4_4",
    "SHEPPARD_1999_EQ_4_5",
    "SHEPPARD_STICKING_FRICTION_FACTOR_RANGE",
    "SHEPPARD_1999_TABLE_4_1_AA6063",
    "SourceKind",
    "SourceRef",
    "SpecificEnergyBasis",
    "UNIVERSAL_GAS_CONSTANT_J_MOL_K",
    "check_force_capacity",
    "check_press_force_capacity",
    "axisymmetric_pressure_breakdown",
    "axisymmetric_steady_deformation_pressure_mpa",
    "axisymmetric_steady_pressure_mpa",
    "breakthrough_pressure_increment_mpa",
    "breakthrough_pressure_increment_mpa_from_log_z",
    "container_friction_pressure_increment_mpa",
    "circular_area_m2_from_diameter_mm",
    "compare_specific_energy_kwh_per_tonne",
    "energy_kwh_from_constant_power_kw",
    "equivalent_extrudate_diameter_mm",
    "flow_l_min_from_area_m2_speed_mm_s",
    "flow_stress_mpa",
    "force_mn_from_specific_pressure_mpa",
    "hydraulic_force_contribution_mn_from_pressure_bar",
    "hydraulic_pressure_bar_from_force_contribution_mn",
    "hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min",
    "log_zener_hollomon_parameter",
    "modified_feltham_mean_strain_rate_s_1",
    "ram_power_kw_from_force_mn_speed_mm_s",
    "ram_work_kwh_from_constant_force_mn_stroke_mm",
    "sheppard_deformation_semiangle_deg",
    "specific_energy_kwh_per_tonne",
    "specific_pressure_mpa_from_force_mn",
    "steady_state_flow_stress_mpa",
    "steady_state_flow_stress_mpa_from_log_z",
    "true_strain_from_extrusion_ratio",
    "upset_billet_length_mm",
    "zener_hollomon_parameter_s_1",
]
