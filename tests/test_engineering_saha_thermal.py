import math

import pytest

from pyextrusion.engineering import (
    SAHA_AXISYMMETRIC_SEMIDEAD_ZONE_ANGLE_DEG,
    SahaThermalSourceTerms,
    saha_billet_container_heat_flux_w_m2,
    saha_complete_sticking_die_bearing_heat_flux_w_m2,
    saha_complete_sticking_shear_stress_mpa,
    saha_complete_sticking_thermal_source_terms,
    saha_dead_metal_zone_heat_flux_w_m2,
    saha_dead_metal_zone_material_speed_mm_s,
    saha_deformation_heat_generation_w_m3,
    saha_die_bearing_heat_flux_w_m2,
)


def test_saha_source_model_keeps_documented_45_degree_dmz_angle():
    assert SAHA_AXISYMMETRIC_SEMIDEAD_ZONE_ANGLE_DEG == pytest.approx(45.0)


def test_saha_deformation_heat_generation_si_regression():
    value = saha_deformation_heat_generation_w_m3(
        flow_stress_mpa=28.0,
        mean_strain_rate_s_1=4.0,
    )

    assert value == pytest.approx(112_000_000.0)


def test_saha_complete_sticking_shear_stress_uses_von_mises():
    value = saha_complete_sticking_shear_stress_mpa(28.0)

    assert value == pytest.approx(28.0 / math.sqrt(3.0))


def test_saha_billet_container_heat_flux_regression():
    value = saha_billet_container_heat_flux_w_m2(
        flow_stress_mpa=28.0,
        ram_speed_mm_s=10.0,
    )

    assert value == pytest.approx(161_658.07537309523)


def test_saha_dead_metal_zone_speed_and_heat_flux_regression():
    speed = saha_dead_metal_zone_material_speed_mm_s(10.0)
    flux = saha_dead_metal_zone_heat_flux_w_m2(
        flow_stress_mpa=28.0,
        ram_speed_mm_s=10.0,
    )

    assert speed == pytest.approx(10.0 / math.cos(math.radians(45.0)))
    assert flux == pytest.approx(228_619.04265976328)


def test_saha_die_bearing_heat_flux_accepts_explicit_friction_stress():
    value = saha_die_bearing_heat_flux_w_m2(
        friction_stress_mpa=10.0,
        exit_speed_m_min=18.0,
    )

    assert value == pytest.approx(3_000_000.0)


def test_saha_complete_sticking_die_bearing_heat_flux_regression():
    value = saha_complete_sticking_die_bearing_heat_flux_w_m2(
        flow_stress_mpa=28.0,
        exit_speed_m_min=22.0,
    )

    assert value == pytest.approx(5_927_462.763680157)


def test_saha_source_terms_bundle_is_non_contradictory():
    result = saha_complete_sticking_thermal_source_terms(
        flow_stress_mpa=28.0,
        mean_strain_rate_s_1=4.0,
        ram_speed_mm_s=10.0,
        exit_speed_m_min=22.0,
    )

    assert isinstance(result, SahaThermalSourceTerms)
    assert result.bearing_friction_stress_mpa == pytest.approx(28.0 / math.sqrt(3.0))
    assert result.deformation_heat_generation_w_m3 == pytest.approx(112_000_000.0)
    assert result.billet_container_heat_flux_w_m2 == pytest.approx(161_658.07537309523)
    assert result.dead_metal_zone_material_speed_mm_s == pytest.approx(
        10.0 / math.cos(math.radians(45.0))
    )
    assert result.dead_metal_zone_heat_flux_w_m2 == pytest.approx(228_619.04265976328)
    assert result.die_bearing_heat_flux_w_m2 == pytest.approx(5_927_462.763680157)
    assert result.model_scope == "saha_local_thermal_source_terms_only"
    assert len(result.provenance) == 2

    data = result.to_dict()
    assert data["deformation_heat_generation_w_m3"] == pytest.approx(
        result.deformation_heat_generation_w_m3
    )
    assert data["die_bearing_heat_flux_w_m2"] == pytest.approx(
        result.die_bearing_heat_flux_w_m2
    )


def test_saha_source_terms_do_not_imply_an_exit_temperature():
    result = saha_complete_sticking_thermal_source_terms(
        flow_stress_mpa=28.0,
        mean_strain_rate_s_1=4.0,
        ram_speed_mm_s=10.0,
        exit_speed_m_min=22.0,
    )

    assert not hasattr(result, "exit_temperature_c")
    assert not hasattr(result, "temperature_rise_c")


def test_saha_source_terms_are_monotonic_at_fixed_other_inputs():
    assert saha_deformation_heat_generation_w_m3(28.0, 5.0) > saha_deformation_heat_generation_w_m3(
        28.0, 2.0
    )
    assert saha_billet_container_heat_flux_w_m2(28.0, 12.0) > saha_billet_container_heat_flux_w_m2(
        28.0, 6.0
    )
    assert saha_dead_metal_zone_heat_flux_w_m2(28.0, 12.0) > saha_dead_metal_zone_heat_flux_w_m2(
        28.0, 6.0
    )
    assert saha_die_bearing_heat_flux_w_m2(12.0, 24.0) > saha_die_bearing_heat_flux_w_m2(
        12.0, 12.0
    )


def test_zero_stress_or_speed_produces_zero_source_term():
    assert saha_deformation_heat_generation_w_m3(0.0, 4.0) == pytest.approx(0.0)
    assert saha_deformation_heat_generation_w_m3(28.0, 0.0) == pytest.approx(0.0)
    assert saha_billet_container_heat_flux_w_m2(28.0, 0.0) == pytest.approx(0.0)
    assert saha_dead_metal_zone_heat_flux_w_m2(28.0, 0.0) == pytest.approx(0.0)
    assert saha_die_bearing_heat_flux_w_m2(12.0, 0.0) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "call",
    [
        lambda: saha_deformation_heat_generation_w_m3(-1.0, 4.0),
        lambda: saha_deformation_heat_generation_w_m3(28.0, -1.0),
        lambda: saha_complete_sticking_shear_stress_mpa(-1.0),
        lambda: saha_billet_container_heat_flux_w_m2(28.0, -1.0),
        lambda: saha_dead_metal_zone_material_speed_mm_s(-1.0),
        lambda: saha_dead_metal_zone_heat_flux_w_m2(28.0, -1.0),
        lambda: saha_die_bearing_heat_flux_w_m2(-1.0, 20.0),
        lambda: saha_die_bearing_heat_flux_w_m2(10.0, -1.0),
        lambda: SahaThermalSourceTerms(28.0, 4.0, 10.0, 22.0, -1.0),
    ],
)
def test_saha_source_model_rejects_negative_inputs(call):
    with pytest.raises(ValueError):
        call()


def test_extreme_saha_inputs_cannot_silently_return_nonfinite_values():
    with pytest.raises(ValueError):
        saha_deformation_heat_generation_w_m3(1.0e308, 1.0e308)
