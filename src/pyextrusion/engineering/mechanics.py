from __future__ import annotations

import math


def _positive_finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be a finite value greater than zero")
    return number


def circular_area_m2_from_diameter_mm(diameter_mm: float) -> float:
    """Return circular area in m² from a diameter supplied in millimetres."""
    diameter = _positive_finite(diameter_mm, "diameter_mm") / 1000.0
    return math.pi * diameter * diameter / 4.0


def true_strain_from_extrusion_ratio(extrusion_ratio: float) -> float:
    """Return ideal logarithmic extrusion strain, epsilon = ln(R).

    R=1 is valid and returns zero strain. Values below one are rejected because
    they do not represent a reduction ratio for direct extrusion.
    """
    ratio = float(extrusion_ratio)
    if not math.isfinite(ratio) or ratio < 1.0:
        raise ValueError("extrusion_ratio must be finite and >= 1")
    return math.log(ratio)


def specific_pressure_mpa_from_force_mn(force_mn: float, area_m2: float) -> float:
    """Return specific pressure in MPa from axial force in MN and area in m².

    This function is unit-explicit and agnostic to the physical origin of the
    force. For extrusion pressure, pass the internal container-bore area.
    """
    force = _positive_finite(force_mn, "force_mn")
    area = _positive_finite(area_m2, "area_m2")
    return force / area


def force_mn_from_specific_pressure_mpa(specific_pressure_mpa: float, area_m2: float) -> float:
    """Return axial force in MN from specific pressure in MPa and area in m²."""
    pressure = _positive_finite(specific_pressure_mpa, "specific_pressure_mpa")
    area = _positive_finite(area_m2, "area_m2")
    return pressure * area


def hydraulic_force_mn_from_pressure_bar(hydraulic_pressure_bar: float, effective_area_m2: float) -> float:
    """Return hydraulic force in MN from hydraulic pressure and effective area.

    Hydraulic pressure is intentionally expressed in bar here so it cannot be
    confused with extrusion-specific pressure in MPa.
    """
    pressure_bar = _positive_finite(hydraulic_pressure_bar, "hydraulic_pressure_bar")
    area = _positive_finite(effective_area_m2, "effective_area_m2")
    return pressure_bar * 1.0e5 * area / 1.0e6


def hydraulic_pressure_bar_from_force_mn(force_mn: float, effective_area_m2: float) -> float:
    """Return hydraulic pressure in bar from force in MN and effective area."""
    force = _positive_finite(force_mn, "force_mn")
    area = _positive_finite(effective_area_m2, "effective_area_m2")
    return force * 1.0e6 / area / 1.0e5
