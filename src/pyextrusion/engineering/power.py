from __future__ import annotations

import math
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


def _finite_result(value: float, field: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field} is outside the representable finite range")
    return value


def _nonempty_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min(
    pressure_bar: float,
    flow_l_min: float,
) -> float:
    """Return one ideal pressure-flow power contribution, ``P = p Q``.

    With pressure in bar and volumetric flow in L/min::

        P[kW] = p[bar] * Q[L/min] / 600

    Pressure and flow must describe the same hydraulic boundary and operating
    point. The pressure is relative to a caller-declared reference (or may be a
    declared pressure drop across a component) and the flow must cross that
    same boundary. The result is not automatically pump-shaft power, electrical
    consumption, or net cylinder/ram power. Multi-chamber systems require a
    signed balance of their individual pressure-flow contributions.

    Products of independently documented maxima, or products of separate mean
    pressure and mean flow values, must not be interpreted as a real operating
    power unless simultaneity has independently been established.
    """
    pressure = _nonnegative(pressure_bar, "pressure_bar")
    flow = _nonnegative(flow_l_min, "flow_l_min")
    return _finite_result((pressure / 600.0) * flow, "hydraulic pressure-flow power")


def ram_power_kw_from_force_mn_speed_mm_s(
    force_mn: float,
    ram_speed_mm_s: float,
) -> float:
    """Return axial mechanical power in kW from ``P = F v``.

    With force in MN and ram speed in mm/s the numeric product is directly kW:
    ``1 MN * 1 mm/s = 1 kW``.

    Force and speed must refer to the same point and direction of motion. The
    identity does not predict extrusion force and does not assert that a press
    can sustain the supplied force and speed simultaneously.
    """
    force = _nonnegative(force_mn, "force_mn")
    speed = _nonnegative(ram_speed_mm_s, "ram_speed_mm_s")
    return _finite_result(force * speed, "ram mechanical power")


def energy_kwh_from_constant_power_kw(
    power_kw: float,
    duration_s: float,
) -> float:
    """Return energy in kWh for constant supplied power over a duration."""
    power = _nonnegative(power_kw, "power_kw")
    duration = _nonnegative(duration_s, "duration_s")
    return _finite_result(power * (duration / 3600.0), "constant-power energy")


def ram_work_kwh_from_constant_force_mn_stroke_mm(
    force_mn: float,
    stroke_mm: float,
) -> float:
    """Return axial ram work in kWh for constant force over a stroke.

    This is ``W = F x`` evaluated for a constant supplied force. It is not an
    integration of a real extrusion-force curve and should not be presented as
    such when force varies through the stroke.
    """
    force = _nonnegative(force_mn, "force_mn")
    stroke = _nonnegative(stroke_mm, "stroke_mm")
    return _finite_result(force * (stroke / 3600.0), "constant-force ram work")


def specific_energy_kwh_per_tonne(
    energy_kwh: float,
    mass_kg: float,
) -> float:
    """Return supplied energy normalized by a declared mass basis in kWh/t.

    The arithmetic is agnostic to the energy boundary and to what the mass
    represents. Before presentation or comparison the caller must identify, for
    example, whether energy is electrical, hydraulic-fluid or ram-mechanical,
    and whether mass is billet input, extruded mass, gross product, net product
    or accepted product. ``kWh/t`` alone does not establish comparability.
    """
    energy = _nonnegative(energy_kwh, "energy_kwh")
    mass = _positive(mass_kg, "mass_kg")
    # Divide before multiplying so equal very-large finite values remain
    # representable instead of overflowing an intermediate product.
    return _finite_result((energy / mass) * 1000.0, "specific energy")


@dataclass(frozen=True)
class SpecificEnergyBasis:
    """Declared common context for a specific-energy comparison.

    These labels are caller-supplied metadata, not independently verified by
    PyExtrusion. A comparison function accepts one shared basis so both numeric
    values are explicitly presented under the same declared boundary, mass
    denominator and period/scope.
    """

    energy_boundary: str
    mass_basis: str
    period_basis: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "energy_boundary", _nonempty_text(self.energy_boundary, "energy_boundary"))
        object.__setattr__(self, "mass_basis", _nonempty_text(self.mass_basis, "mass_basis"))
        object.__setattr__(self, "period_basis", _nonempty_text(self.period_basis, "period_basis"))

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class EnergyComparison:
    """Arithmetic comparison under one explicitly declared common basis.

    Derived difference and ratio are properties so callers cannot construct a
    self-contradictory result object by supplying inconsistent dependent fields.
    """

    reference_kwh_per_t: float
    candidate_kwh_per_t: float
    basis: SpecificEnergyBasis

    def __post_init__(self) -> None:
        reference = _positive(self.reference_kwh_per_t, "reference_kwh_per_t")
        candidate = _nonnegative(self.candidate_kwh_per_t, "candidate_kwh_per_t")
        if not isinstance(self.basis, SpecificEnergyBasis):
            raise ValueError("basis must be a SpecificEnergyBasis")
        ratio = candidate / reference
        if not math.isfinite(ratio):
            raise ValueError("specific-energy comparison ratio is outside the representable finite range")
        object.__setattr__(self, "reference_kwh_per_t", reference)
        object.__setattr__(self, "candidate_kwh_per_t", candidate)

    @property
    def delta_kwh_per_t(self) -> float:
        return self.candidate_kwh_per_t - self.reference_kwh_per_t

    @property
    def candidate_to_reference_ratio(self) -> float:
        return self.candidate_kwh_per_t / self.reference_kwh_per_t

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_kwh_per_t": self.reference_kwh_per_t,
            "candidate_kwh_per_t": self.candidate_kwh_per_t,
            "delta_kwh_per_t": self.delta_kwh_per_t,
            "candidate_to_reference_ratio": self.candidate_to_reference_ratio,
            "basis": self.basis.to_dict(),
        }


def compare_specific_energy_kwh_per_tonne(
    reference_kwh_per_t: float,
    candidate_kwh_per_t: float,
    *,
    basis: SpecificEnergyBasis,
) -> EnergyComparison:
    """Compare two specific-energy values under one caller-declared basis.

    The ratio is ``candidate / reference``. The shared ``basis`` makes the
    caller state the energy boundary, mass denominator and period/scope used by
    both values. PyExtrusion does not independently verify those declarations
    and does not infer savings, efficiency, causality, ranking or process
    superiority from the ratio.
    """
    return EnergyComparison(
        reference_kwh_per_t=reference_kwh_per_t,
        candidate_kwh_per_t=candidate_kwh_per_t,
        basis=basis,
    )
