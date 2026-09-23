import math

import pytest

from pyextrusion.engineering import (
    AA6063_SHEPPARD_1999,
    AxisymmetricPressureBreakdown,
    SHEPPARD_STICKING_FRICTION_FACTOR_RANGE,
    axisymmetric_pressure_breakdown,
    axisymmetric_steady_deformation_pressure_mpa,
    axisymmetric_steady_pressure_mpa,
    breakthrough_pressure_increment_mpa,
    breakthrough_pressure_increment_mpa_from_log_z,
    container_friction_pressure_increment_mpa,
    flow_stress_mpa,
    log_zener_hollomon_parameter,
    modified_feltham_mean_strain_rate_s_1,
    upset_billet_length_mm,
    zener_hollomon_parameter_s_1,
)


def test_sheppard_reported_sticking_friction_range_is_metadata_not_a_default():
    assert SHEPPARD_STICKING_FRICTION_FACTOR_RANGE.lower == pytest.approx(0.8)
    assert SHEPPARD_STICKING_FRICTION_FACTOR_RANGE.upper == pytest.approx(0.9)


def test_upset_billet_length_conserves_cylindrical_volume():
    length = upset_billet_length_mm(
        billet_diameter_mm=228.0,
        billet_length_mm=1300.0,
        container_diameter_mm=236.0,
    )

    assert length == pytest.approx(1213.358230393565)
    assert 228.0**2 * 1300.0 == pytest.approx(236.0**2 * length)


def test_eq_4_3_steady_deformation_pressure_regression():
    pressure = axisymmetric_steady_deformation_pressure_mpa(
        flow_stress_mpa=28.1793602854981,
        extrusion_ratio=31.2,
    )

    assert pressure == pytest.approx(185.08523404958936)


def test_container_friction_increment_is_zero_without_friction_or_contact_length():
    assert container_friction_pressure_increment_mpa(30.0, 0.0, 1000.0, 236.0) == pytest.approx(0.0)
    assert container_friction_pressure_increment_mpa(30.0, 0.88, 0.0, 236.0) == pytest.approx(0.0)


def test_eq_4_4_steady_pressure_uses_source_rounded_coefficient():
    pressure = axisymmetric_steady_pressure_mpa(
        flow_stress_mpa=28.1793602854981,
        extrusion_ratio=31.2,
        friction_factor_m=0.88,
        billet_contact_length_mm=1213.358230393565,
        container_diameter_mm=236.0,
    )

    assert pressure == pytest.approx(479.5789247928336)


def test_eq_4_5_breakthrough_increment_regression():
    strain_rate = modified_feltham_mean_strain_rate_s_1(11.75, 236.0, 31.2)
    ln_z = log_zener_hollomon_parameter(strain_rate, 470.0, AA6063_SHEPPARD_1999)
    z_value = zener_hollomon_parameter_s_1(strain_rate, 470.0, AA6063_SHEPPARD_1999)

    from_log = breakthrough_pressure_increment_mpa_from_log_z(ln_z, AA6063_SHEPPARD_1999)
    from_z = breakthrough_pressure_increment_mpa(z_value, AA6063_SHEPPARD_1999)

    assert from_log == pytest.approx(14.060773552463742)
    assert from_z == pytest.approx(from_log)


def test_breakthrough_correlation_is_not_silently_clipped_outside_useful_range():
    negative = breakthrough_pressure_increment_mpa_from_log_z(
        AA6063_SHEPPARD_1999.ln_A - 10.0,
        AA6063_SHEPPARD_1999,
    )

    assert negative < 0.0

    with pytest.raises(ValueError, match="breakthrough_increment_mpa"):
        AxisymmetricPressureBreakdown(
            flow_stress_mpa=20.0,
            extrusion_ratio=20.0,
            friction_factor_m=0.88,
            billet_contact_length_mm=1000.0,
            container_diameter_mm=236.0,
            breakthrough_increment_mpa=negative,
        )


def test_axisymmetric_pressure_breakdown_regression_for_uniform_470c_case():
    strain_rate = modified_feltham_mean_strain_rate_s_1(11.75, 236.0, 31.2)
    ln_z = log_zener_hollomon_parameter(strain_rate, 470.0, AA6063_SHEPPARD_1999)
    flow_stress = flow_stress_mpa(strain_rate, 470.0, AA6063_SHEPPARD_1999)
    contact_length = upset_billet_length_mm(228.0, 1300.0, 236.0)
    breakthrough = breakthrough_pressure_increment_mpa_from_log_z(ln_z, AA6063_SHEPPARD_1999)

    result = axisymmetric_pressure_breakdown(
        flow_stress_mpa=flow_stress,
        extrusion_ratio=31.2,
        friction_factor_m=0.88,
        billet_contact_length_mm=contact_length,
        container_diameter_mm=236.0,
        breakthrough_increment_mpa=breakthrough,
    )

    assert result.flow_stress_mpa == pytest.approx(28.1793602854981)
    assert result.deformation_pressure_mpa == pytest.approx(185.14340331820532)
    assert result.container_friction_pressure_mpa == pytest.approx(294.43552147462833)
    assert result.steady_pressure_mpa == pytest.approx(479.5789247928336)
    assert result.breakthrough_increment_mpa == pytest.approx(14.060773552463742)
    assert result.peak_pressure_mpa == pytest.approx(493.63969834529735)
    assert result.required_force_mn == pytest.approx(21.593545969198164)
    assert result.model_scope == "axisymmetric_equivalent_direct_extrusion"
    assert len(result.provenance) == 3

    data = result.to_dict()
    assert data["peak_pressure_mpa"] == pytest.approx(result.peak_pressure_mpa)
    assert data["required_force_mn"] == pytest.approx(result.required_force_mn)


def test_axisymmetric_pressure_breakdown_derived_fields_cannot_be_supplied_inconsistently():
    result = AxisymmetricPressureBreakdown(
        flow_stress_mpa=30.0,
        extrusion_ratio=20.0,
        friction_factor_m=0.85,
        billet_contact_length_mm=800.0,
        container_diameter_mm=210.0,
        breakthrough_increment_mpa=10.0,
    )

    expected_peak = (
        result.deformation_pressure_mpa
        + result.container_friction_pressure_mpa
        + result.breakthrough_increment_mpa
    )
    assert result.peak_pressure_mpa == pytest.approx(expected_peak)
    assert math.isfinite(result.required_force_mn)


@pytest.mark.parametrize(
    "call",
    [
        lambda: upset_billet_length_mm(237.0, 1000.0, 236.0),
        lambda: upset_billet_length_mm(228.0, 0.0, 236.0),
        lambda: axisymmetric_steady_deformation_pressure_mpa(30.0, 1.0),
        lambda: axisymmetric_steady_deformation_pressure_mpa(30.0, 100.0001),
        lambda: axisymmetric_steady_deformation_pressure_mpa(-1.0, 30.0),
        lambda: container_friction_pressure_increment_mpa(30.0, 1.01, 1000.0, 236.0),
        lambda: container_friction_pressure_increment_mpa(30.0, -0.01, 1000.0, 236.0),
        lambda: container_friction_pressure_increment_mpa(30.0, 0.88, 1000.0, 0.0),
        lambda: breakthrough_pressure_increment_mpa(0.0, AA6063_SHEPPARD_1999),
        lambda: breakthrough_pressure_increment_mpa(1.0e10, "AA6063"),
    ],
)
def test_phase2_pressure_equations_reject_invalid_or_out_of_scope_inputs(call):
    with pytest.raises(ValueError):
        call()
