"""Engineering foundations for advanced PyExtrusion models.

This package contains press-independent equations and traceability models.
Press-specific limits, hydraulic layouts and plant data must be supplied as
configuration rather than embedded in these equations.
"""

from .metadata import Confidence, EngineeringResult, EstimateKind, Interval, SourceKind, SourceRef
from .mechanics import (
    circular_area_m2_from_diameter_mm,
    force_mn_from_specific_pressure_mpa,
    hydraulic_force_mn_from_pressure_bar,
    hydraulic_pressure_bar_from_force_mn,
    specific_pressure_mpa_from_force_mn,
    true_strain_from_extrusion_ratio,
)

__all__ = [
    "Confidence",
    "EngineeringResult",
    "EstimateKind",
    "Interval",
    "SourceKind",
    "SourceRef",
    "circular_area_m2_from_diameter_mm",
    "force_mn_from_specific_pressure_mpa",
    "hydraulic_force_mn_from_pressure_bar",
    "hydraulic_pressure_bar_from_force_mn",
    "specific_pressure_mpa_from_force_mn",
    "true_strain_from_extrusion_ratio",
]
