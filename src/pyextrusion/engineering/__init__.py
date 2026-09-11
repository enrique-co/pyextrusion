"""Engineering foundations for advanced PyExtrusion models.

This package contains press-independent equations and traceability models.
Press-specific limits, hydraulic layouts and plant data must be supplied as
configuration rather than embedded in these equations.
"""

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

__all__ = [
    "Confidence",
    "EnergyComparison",
    "EngineeringResult",
    "EstimateKind",
    "ForceCapacityCheck",
    "ForceLimitSource",
    "HydraulicSystemSpec",
    "InstalledPowerKind",
    "Interval",
    "PressEngineeringSpec",
    "RamOperatingRange",
    "SourceKind",
    "SourceRef",
    "SpecificEnergyBasis",
    "check_force_capacity",
    "check_press_force_capacity",
    "circular_area_m2_from_diameter_mm",
    "compare_specific_energy_kwh_per_tonne",
    "energy_kwh_from_constant_power_kw",
    "flow_l_min_from_area_m2_speed_mm_s",
    "force_mn_from_specific_pressure_mpa",
    "hydraulic_force_contribution_mn_from_pressure_bar",
    "hydraulic_pressure_bar_from_force_contribution_mn",
    "hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min",
    "ram_power_kw_from_force_mn_speed_mm_s",
    "ram_work_kwh_from_constant_force_mn_stroke_mm",
    "specific_energy_kwh_per_tonne",
    "specific_pressure_mpa_from_force_mn",
    "true_strain_from_extrusion_ratio",
]
