from __future__ import annotations

import math

from .._strict import require_number


def _nonnegative_finite(value: float, name: str) -> float:
    number = require_number(value, name, ValueError, minimum=0.0)
    assert number is not None
    return number


def _positive_finite(value: float, name: str) -> float:
    number = require_number(value, name, ValueError, minimum=0.0, exclusive_minimum=True)
    assert number is not None
    return number


def _finite_result(value: float, name: str, *, positive: bool = False) -> float:
    if not math.isfinite(value) or (positive and value <= 0.0):
        raise ValueError(f"{name} is outside the representable finite range")
    return value


def circular_area_m2_from_diameter_mm(diameter_mm: float) -> float:
    """Return circular area in m² from a positive diameter in millimetres."""
    diameter_m = _positive_finite(diameter_mm, "diameter_mm") / 1000.0
    area = math.pi * diameter_m * diameter_m / 4.0
    return _finite_result(area, "circular area", positive=True)


def true_strain_from_extrusion_ratio(extrusion_ratio: float) -> float:
    """Return ideal logarithmic reduction strain, ``epsilon = ln(R)``.

    For direct extrusion in PyExtrusion, ``R`` is the container-bore area
    divided by the total simultaneously extruded profile area. The result is an
    ideal scalar reduction measure; it is not a local strain field or a claim
    about the accumulated strain of an individual material trajectory.

    ``R = 1`` is valid and returns zero. Values below one are rejected because
    they do not represent a reduction ratio under this convention.
    """
    ratio = require_number(extrusion_ratio, "extrusion_ratio", ValueError, minimum=1.0)
    assert ratio is not None
    return _finite_result(math.log(ratio), "true strain")


def specific_pressure_mpa_from_force_mn(force_mn: float, area_m2: float) -> float:
    """Return equivalent axial specific pressure in MPa from ``F / A``.

    The supplied force is normalized by the supplied area. For the conventional
    extrusion-specific-pressure quantity used by PyExtrusion, pass the internal
    container-bore area. This scalar is not a local metal-pressure field and it
    does not predict the pressure or force required by an extrusion process.
    """
    force = _nonnegative_finite(force_mn, "force_mn")
    area = _positive_finite(area_m2, "area_m2")
    return _finite_result(force / area, "specific pressure")


def force_mn_from_specific_pressure_mpa(specific_pressure_mpa: float, area_m2: float) -> float:
    """Return axial force in MN from an equivalent specific pressure and area.

    This is the inverse normalization ``F = p A``. It does not establish how a
    real press generates the force or whether the pressure is physically
    attainable under a particular extrusion condition.
    """
    pressure = _nonnegative_finite(specific_pressure_mpa, "specific_pressure_mpa")
    area = _positive_finite(area_m2, "area_m2")
    return _finite_result(pressure * area, "axial force")


def hydraulic_force_contribution_mn_from_pressure_bar(
    hydraulic_pressure_bar: float,
    pressure_force_area_m2: float,
) -> float:
    """Return one ideal hydraulic pressure-area force contribution in MN.

    The identity is ``F = p A`` for one explicitly identified pressure and its
    corresponding effective pressure-force area. The pressure must be
    interpreted relative to a caller-declared reference. The result is a force
    contribution, not automatically the net ram force: opposing chambers,
    multiple actuators, return pressure and other loads require their own
    signed balance outside this primitive.
    """
    pressure_bar = _nonnegative_finite(hydraulic_pressure_bar, "hydraulic_pressure_bar")
    area = _positive_finite(pressure_force_area_m2, "pressure_force_area_m2")
    force = pressure_bar * 1.0e5 * area / 1.0e6
    return _finite_result(force, "hydraulic force contribution")


def hydraulic_pressure_bar_from_force_contribution_mn(
    force_contribution_mn: float,
    pressure_force_area_m2: float,
) -> float:
    """Invert one ideal hydraulic ``p A`` force contribution.

    The supplied force must be the contribution associated with the same
    effective area. A net actuator or ram force cannot in general be inverted
    to a chamber pressure without resolving the other pressure-area terms.
    """
    force = _nonnegative_finite(force_contribution_mn, "force_contribution_mn")
    area = _positive_finite(pressure_force_area_m2, "pressure_force_area_m2")
    pressure = force * 1.0e6 / area / 1.0e5
    return _finite_result(pressure, "hydraulic pressure")


def flow_l_min_from_area_m2_speed_mm_s(area_m2: float, speed_mm_s: float) -> float:
    """Return ideal volumetric flow from one area and normal velocity, ``Q=Av``.

    The area and speed must refer to the same moving fluid boundary. This
    kinematic identity does not represent leakage, compressibility, valve flow
    or the combined flow demand of multiple chambers.
    """
    area = _positive_finite(area_m2, "area_m2")
    speed = _nonnegative_finite(speed_mm_s, "speed_mm_s")
    # m² * mm/s * 60 converts directly to L/min.
    return _finite_result(area * speed * 60.0, "volumetric flow")
