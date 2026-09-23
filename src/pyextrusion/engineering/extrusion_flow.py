from __future__ import annotations

import math

from .._strict import require_number


def equivalent_extrudate_diameter_mm(
    container_diameter_mm: float,
    extrusion_ratio: float,
) -> float:
    """Return equivalent circular extrudate diameter in millimetres.

    The equivalent diameter preserves the total simultaneously extruded area
    under R = A_container / A_extrudate. It is an axisymmetric equivalent
    geometry and does not claim that a shaped profile is circular.
    """
    diameter = require_number(
        container_diameter_mm,
        "container_diameter_mm",
        ValueError,
        minimum=0.0,
        exclusive_minimum=True,
    )
    ratio = require_number(
        extrusion_ratio,
        "extrusion_ratio",
        ValueError,
        minimum=1.0,
        exclusive_minimum=True,
    )
    assert diameter is not None and ratio is not None
    value = diameter / math.sqrt(ratio)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("equivalent extrudate diameter is outside the representable finite range")
    return value


def sheppard_deformation_semiangle_deg(extrusion_ratio: float) -> float:
    """Return the empirical deformation-zone semiangle in degrees.

    Uses alpha = 38.7 + 6.9 ln(R), as reported by Sheppard from the optimized
    upper-bound treatment used with the modified Feltham mean strain-rate model.
    """
    ratio = require_number(
        extrusion_ratio,
        "extrusion_ratio",
        ValueError,
        minimum=1.0,
        exclusive_minimum=True,
    )
    assert ratio is not None
    angle = 38.7 + 6.9 * math.log(ratio)
    if not math.isfinite(angle) or not 0.0 < angle < 90.0:
        raise ValueError("calculated deformation semiangle lies outside the physical 0-90 degree range")
    return angle


def modified_feltham_mean_strain_rate_s_1(
    ram_speed_mm_s: float,
    container_diameter_mm: float,
    extrusion_ratio: float,
    *,
    deformation_semiangle_deg: float | None = None,
) -> float:
    """Return mean equivalent extrusion strain rate in s^-1.

    The model is the modified Feltham relation presented by Sheppard for direct
    extrusion:

        e_dot = 6 V_R D_B^2 (0.171 + 1.86 ln R) tan(alpha)
                / (D_B^3 - D_E^3)

    with D_E = D_B / sqrt(R). V_R and the diameters may all be supplied in
    millimetres and seconds because the length units cancel.

    If deformation_semiangle_deg is omitted, alpha is evaluated with
    38.7 + 6.9 ln(R). A caller-supplied angle is treated as an explicit model
    input and is not inferred or corrected by PyExtrusion.

    This is a scalar mean strain-rate model for the deformation zone, not a
    local strain-rate field.
    """
    speed = require_number(ram_speed_mm_s, "ram_speed_mm_s", ValueError, minimum=0.0)
    diameter = require_number(
        container_diameter_mm,
        "container_diameter_mm",
        ValueError,
        minimum=0.0,
        exclusive_minimum=True,
    )
    ratio = require_number(
        extrusion_ratio,
        "extrusion_ratio",
        ValueError,
        minimum=1.0,
        exclusive_minimum=True,
    )
    assert speed is not None and diameter is not None and ratio is not None

    if deformation_semiangle_deg is None:
        angle = sheppard_deformation_semiangle_deg(ratio)
    else:
        angle_value = require_number(
            deformation_semiangle_deg,
            "deformation_semiangle_deg",
            ValueError,
            minimum=0.0,
            maximum=90.0,
            exclusive_minimum=True,
        )
        assert angle_value is not None
        if angle_value >= 90.0:
            raise ValueError("deformation_semiangle_deg must be < 90")
        angle = angle_value

    equivalent_diameter = equivalent_extrudate_diameter_mm(diameter, ratio)
    denominator = diameter**3 - equivalent_diameter**3
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("modified Feltham denominator must be positive and finite")

    geometry_factor = 0.171 + 1.86 * math.log(ratio)
    value = (
        6.0
        * speed
        * diameter**2
        * geometry_factor
        * math.tan(math.radians(angle))
        / denominator
    )
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("mean equivalent strain rate is outside the representable finite range")
    return value
