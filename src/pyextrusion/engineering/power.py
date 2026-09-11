from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number


def _nonnegative(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0)
    assert result is not None
    return result


def _positive(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0, exclusive_minimum=True)
    assert result is not None
    return result


def hydraulic_power_kw_from_pressure_bar_flow_l_min(
    pressure_bar: float,
    flow_l_min: float,
) -> float:
    """Return ideal hydraulic fluid power in kW for a supplied operating point.

    The identity is ``P = p Q`` with pressure supplied in bar and volumetric
    flow in L/min::

        P[kW] = p[bar] * Q[L/min] / 600

    This is ideal hydraulic power in the fluid. It does not include pump,
    motor, valve or line losses and it does not assert that a press can sustain
    the supplied pressure and flow simultaneously.
    """
    pressure = _nonnegative(pressure_bar, "pressure_bar")
    flow = _nonnegative(flow_l_min, "flow_l_min")
    return pressure * flow / 600.0


def ram_power_kw_from_force_mn_speed_mm_s(
    force_mn: float,
    ram_speed_mm_s: float,
) -> float:
    """Return ideal axial ram mechanical power in kW from ``P = F v``.

    With force in MN and ram speed in mm/s the numeric product is directly kW:
    ``1 MN * 1 mm/s = 1 kW``.

    The calculation assumes force acts in the direction of ram travel. It does
    not predict the extrusion force and does not assert that the press can
    deliver the supplied force and speed simultaneously.
    """
    force = _nonnegative(force_mn, "force_mn")
    speed = _nonnegative(ram_speed_mm_s, "ram_speed_mm_s")
    return force * speed


def energy_kwh_from_constant_power_kw(
    power_kw: float,
    duration_s: float,
) -> float:
    """Return energy in kWh for constant supplied power over a duration."""
    power = _nonnegative(power_kw, "power_kw")
    duration = _nonnegative(duration_s, "duration_s")
    return power * duration / 3600.0


def ram_work_kwh_from_constant_force_mn_stroke_mm(
    force_mn: float,
    stroke_mm: float,
) -> float:
    """Return ideal axial ram work in kWh for constant force over a stroke.

    This is ``W = F x`` evaluated for a constant supplied force. It is not an
    integration of a real extrusion-force curve and should not be presented as
    such when force varies through the stroke.
    """
    force = _nonnegative(force_mn, "force_mn")
    stroke = _nonnegative(stroke_mm, "stroke_mm")
    return force * stroke / 3600.0


def specific_energy_kwh_per_tonne(
    energy_kwh: float,
    mass_kg: float,
) -> float:
    """Return supplied energy normalized by produced mass in kWh/t.

    The function is agnostic to the energy source. The caller should label the
    result according to whether the input energy is hydraulic, ram-mechanical,
    electrical, measured, estimated or otherwise.
    """
    energy = _nonnegative(energy_kwh, "energy_kwh")
    mass = _positive(mass_kg, "mass_kg")
    return energy * 1000.0 / mass


@dataclass(frozen=True)
class EnergyComparison:
    """Arithmetic comparison of two already normalized energy values."""

    reference_kwh_per_t: float
    candidate_kwh_per_t: float
    delta_kwh_per_t: float
    candidate_to_reference_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_specific_energy_kwh_per_tonne(
    reference_kwh_per_t: float,
    candidate_kwh_per_t: float,
) -> EnergyComparison:
    """Compare two supplied specific-energy values without ranking semantics.

    The ratio is ``candidate / reference``. PyExtrusion does not infer whether
    the values represent electrical consumption, hydraulic energy, ram work or
    total plant energy; that meaning belongs to the caller's data provenance.
    """
    reference = _positive(reference_kwh_per_t, "reference_kwh_per_t")
    candidate = _nonnegative(candidate_kwh_per_t, "candidate_kwh_per_t")
    return EnergyComparison(
        reference_kwh_per_t=reference,
        candidate_kwh_per_t=candidate,
        delta_kwh_per_t=candidate - reference,
        candidate_to_reference_ratio=candidate / reference,
    )
