from __future__ import annotations

import math

from .._strict import require_number
from .materials import HotWorkingConstitutiveModel


def _require_model(model: HotWorkingConstitutiveModel) -> HotWorkingConstitutiveModel:
    if not isinstance(model, HotWorkingConstitutiveModel):
        raise ValueError("model must be a HotWorkingConstitutiveModel")
    return model


def _temperature_k_from_celsius(temperature_c: float) -> float:
    temperature = require_number(
        temperature_c,
        "temperature_c",
        ValueError,
        minimum=-273.15,
        exclusive_minimum=True,
    )
    assert temperature is not None
    return temperature + 273.15


def log_zener_hollomon_parameter(
    mean_strain_rate_s_1: float,
    temperature_c: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return natural logarithm of the Zener-Hollomon parameter.

    Uses ln(Z) = ln(e_dot) + Q / (R T), with temperature in kelvin and
    mean strain rate in s^-1.
    """
    constitutive = _require_model(model)
    strain_rate = require_number(
        mean_strain_rate_s_1,
        "mean_strain_rate_s_1",
        ValueError,
        minimum=0.0,
        exclusive_minimum=True,
    )
    assert strain_rate is not None
    temperature_k = _temperature_k_from_celsius(temperature_c)
    value = math.log(strain_rate) + constitutive.activation_energy_j_mol / (
        constitutive.gas_constant_j_mol_k * temperature_k
    )
    if not math.isfinite(value):
        raise ValueError("log Zener-Hollomon parameter is outside the representable finite range")
    return value


def zener_hollomon_parameter_s_1(
    mean_strain_rate_s_1: float,
    temperature_c: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return Zener-Hollomon parameter Z in s^-1."""
    ln_z = log_zener_hollomon_parameter(mean_strain_rate_s_1, temperature_c, model)
    try:
        value = math.exp(ln_z)
    except OverflowError as exc:
        raise ValueError("Zener-Hollomon parameter is outside the representable finite range") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("Zener-Hollomon parameter is outside the representable finite range")
    return value


def steady_state_flow_stress_mpa_from_log_z(
    ln_z: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return steady-state flow stress in MPa from ln(Z).

    Inverts the Sheppard-Wright hyperbolic-sine relation
    Z = A [sinh(alpha sigma)]^n.
    """
    constitutive = _require_model(model)
    log_z = require_number(ln_z, "ln_z", ValueError)
    assert log_z is not None

    log_argument = (log_z - constitutive.ln_A) / constitutive.n

    if log_argument > 350.0:
        asinh_argument = log_argument + math.log(2.0)
    elif log_argument < -350.0:
        asinh_argument = math.exp(log_argument)
    else:
        asinh_argument = math.asinh(math.exp(log_argument))

    stress = asinh_argument / constitutive.alpha_mpa_inv
    if not math.isfinite(stress) or stress < 0.0:
        raise ValueError("steady-state flow stress is outside the representable finite range")
    return stress


def steady_state_flow_stress_mpa(
    zener_hollomon_s_1: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return steady-state flow stress in MPa from Z in s^-1."""
    z_value = require_number(
        zener_hollomon_s_1,
        "zener_hollomon_s_1",
        ValueError,
        minimum=0.0,
        exclusive_minimum=True,
    )
    assert z_value is not None
    return steady_state_flow_stress_mpa_from_log_z(math.log(z_value), model)


def flow_stress_mpa(
    mean_strain_rate_s_1: float,
    temperature_c: float,
    model: HotWorkingConstitutiveModel,
) -> float:
    """Return steady-state flow stress in MPa for one temperature and mean strain rate."""
    ln_z = log_zener_hollomon_parameter(mean_strain_rate_s_1, temperature_c, model)
    return steady_state_flow_stress_mpa_from_log_z(ln_z, model)
