import math

import pytest

from pyextrusion.engineering import (
    AA6063_SHEPPARD_1999,
    SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES,
    SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES,
    StuweSurfaceExitTemperatureEstimate,
    ThermalMaterialProperties,
    flow_stress_mpa,
    modified_feltham_mean_strain_rate_s_1,
    sheppard_billet_container_interface_temperature_c,
    stuwe_container_heating_depth_mm,
    stuwe_container_wall_temperature_rise_c,
    stuwe_deformation_temperature_rise_c,
    stuwe_die_land_heating_depth_mm,
    stuwe_die_land_temperature_rise_c,
    stuwe_surface_exit_temperature_estimate,
    upset_billet_length_mm,
)


def test_sheppard_aluminium_thermal_properties_match_source_values():
    props = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES

    assert props.thermal_conductivity_w_m_k == pytest.approx(201.0)
    assert props.density_kg_m3 == pytest.approx(2800.0)
    assert props.specific_heat_j_kg_k == pytest.approx(1063.9)
    assert props.thermal_diffusivity_m2_s == pytest.approx(6.74741181367744e-05)
    assert props.provenance[0].source_kind == "literature"


def test_stuwe_deformation_temperature_rise_regression():
    value = stuwe_deformation_temperature_rise_c(
        flow_stress_mpa=28.1793602854981,
        extrusion_ratio=31.2,
    )

    assert value == pytest.approx(18.789831490367444)


def test_stuwe_container_wall_temperature_rise_regression():
    value = stuwe_container_wall_temperature_rise_c(
        flow_stress_mpa=28.1793602854981,
        ram_speed_mm_s=11.75,
        billet_contact_length_mm=1213.358230393565,
    )

    assert value == pytest.approx(19.847075222175725)


def test_stuwe_die_land_temperature_rise_regression():
    value = stuwe_die_land_temperature_rise_c(
        flow_stress_mpa=28.1793602854981,
        exit_speed_m_min=22.0,
        die_land_length_mm=5.0,
    )

    assert value == pytest.approx(7.117111661740605)


def test_stuwe_heating_depth_regressions():
    container_depth = stuwe_container_heating_depth_mm(
        ram_speed_mm_s=11.75,
        billet_contact_length_mm=1213.358230393565,
    )
    die_depth = stuwe_die_land_heating_depth_mm(
        exit_speed_m_min=22.0,
        die_land_length_mm=5.0,
    )

    assert container_depth == pytest.approx(83.47264889276437)
    assert die_depth == pytest.approx(0.9592192715724672)


def test_zero_contact_or_land_length_gives_zero_friction_temperature_rise():
    assert stuwe_container_wall_temperature_rise_c(30.0, 10.0, 0.0) == pytest.approx(0.0)
    assert stuwe_die_land_temperature_rise_c(30.0, 20.0, 0.0) == pytest.approx(0.0)


def test_stuwe_temperature_rises_increase_with_relevant_speed_at_fixed_flow_stress():
    container_slow = stuwe_container_wall_temperature_rise_c(30.0, 5.0, 1000.0)
    container_fast = stuwe_container_wall_temperature_rise_c(30.0, 20.0, 1000.0)
    die_slow = stuwe_die_land_temperature_rise_c(30.0, 10.0, 5.0)
    die_fast = stuwe_die_land_temperature_rise_c(30.0, 40.0, 5.0)

    assert container_fast > container_slow
    assert die_fast > die_slow


def test_stuwe_surface_exit_estimate_integrates_with_aa6063_rheology():
    strain_rate = modified_feltham_mean_strain_rate_s_1(
        ram_speed_mm_s=11.75,
        container_diameter_mm=236.0,
        extrusion_ratio=31.2,
    )
    stress = flow_stress_mpa(
        strain_rate,
        470.0,
        AA6063_SHEPPARD_1999,
    )
    contact_length = upset_billet_length_mm(
        billet_diameter_mm=228.0,
        billet_length_mm=1300.0,
        container_diameter_mm=236.0,
    )

    result = stuwe_surface_exit_temperature_estimate(
        billet_temperature_c=470.0,
        flow_stress_mpa=stress,
        extrusion_ratio=31.2,
        ram_speed_mm_s=11.75,
        billet_contact_length_mm=contact_length,
        exit_speed_m_min=22.0,
        die_land_length_mm=5.0,
    )

    assert isinstance(result, StuweSurfaceExitTemperatureEstimate)
    assert result.deformation_temperature_rise_c == pytest.approx(18.789831490367444)
    assert result.container_wall_temperature_rise_c == pytest.approx(19.847075222175725)
    assert result.die_land_temperature_rise_c == pytest.approx(7.117111661740605)
    assert result.total_temperature_rise_c == pytest.approx(45.754018374283774)
    assert result.estimated_surface_exit_temperature_c == pytest.approx(515.7540183742838)
    assert result.model_scope == "stuwe_three_component_surface_exit_estimate"

    data = result.to_dict()
    assert data["estimated_surface_exit_temperature_c"] == pytest.approx(
        result.estimated_surface_exit_temperature_c
    )
    assert data["thermal_diffusivity_m2_s"] == pytest.approx(
        SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES.thermal_diffusivity_m2_s
    )


def test_custom_thermal_properties_are_used_without_hidden_replacement():
    custom = ThermalMaterialProperties(
        thermal_conductivity_w_m_k=180.0,
        density_kg_m3=2700.0,
        specific_heat_j_kg_k=1000.0,
    )

    default = stuwe_die_land_temperature_rise_c(30.0, 20.0, 5.0)
    changed = stuwe_die_land_temperature_rise_c(30.0, 20.0, 5.0, custom)

    assert changed != pytest.approx(default)
    assert custom.thermal_diffusivity_m2_s == pytest.approx(180.0 / (2700.0 * 1000.0))


@pytest.mark.parametrize(
    "call",
    [
        lambda: ThermalMaterialProperties(0.0, 2800.0, 1063.9),
        lambda: ThermalMaterialProperties(201.0, 0.0, 1063.9),
        lambda: ThermalMaterialProperties(201.0, 2800.0, 0.0),
        lambda: stuwe_deformation_temperature_rise_c(-1.0, 30.0),
        lambda: stuwe_deformation_temperature_rise_c(30.0, 1.0),
        lambda: stuwe_container_heating_depth_mm(0.0, 1000.0),
        lambda: stuwe_die_land_heating_depth_mm(0.0, 5.0),
        lambda: stuwe_surface_exit_temperature_estimate(
            -273.15, 30.0, 30.0, 10.0, 1000.0, 20.0, 5.0
        ),
        lambda: stuwe_surface_exit_temperature_estimate(
            470.0, 30.0, 30.0, 0.0, 1000.0, 20.0, 5.0
        ),
        lambda: stuwe_surface_exit_temperature_estimate(
            470.0, 30.0, 30.0, 10.0, 1000.0, 0.0, 5.0
        ),
    ],
)
def test_stuwe_thermal_model_rejects_invalid_or_singular_inputs(call):
    with pytest.raises(ValueError):
        call()


def test_extreme_thermal_properties_cannot_silently_create_nonfinite_diffusivity():
    props = ThermalMaterialProperties(
        thermal_conductivity_w_m_k=1.0e308,
        density_kg_m3=1.0e-308,
        specific_heat_j_kg_k=1.0,
    )
    with pytest.raises(ValueError, match="thermal diffusivity"):
        _ = props.thermal_diffusivity_m2_s


def test_sheppard_tool_steel_thermal_properties_match_source_values():
    props = SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES

    assert props.thermal_conductivity_w_m_k == pytest.approx(32.65)
    assert props.density_kg_m3 == pytest.approx(7860.0)
    assert props.specific_heat_j_kg_k == pytest.approx(489.76)
    assert props.thermal_effusivity_w_sqrt_s_m2_k == pytest.approx(
        math.sqrt(32.65 * 7860.0 * 489.76)
    )


def test_sheppard_thermal_effusivity_ratio_regression():
    aluminium = SHEPPARD_1999_ALUMINIUM_THERMAL_PROPERTIES
    steel = SHEPPARD_1999_TOOL_STEEL_THERMAL_PROPERTIES

    ratio = (
        steel.thermal_effusivity_w_sqrt_s_m2_k
        / aluminium.thermal_effusivity_w_sqrt_s_m2_k
    )

    assert ratio == pytest.approx(0.4581598976908614)


def test_sheppard_billet_container_interface_temperature_regression():
    value = sheppard_billet_container_interface_temperature_c(
        billet_temperature_c=470.0,
        container_temperature_c=430.0,
    )

    assert value == pytest.approx(457.4318338224387)


def test_sheppard_interface_temperature_is_between_body_temperatures():
    hot_to_cold = sheppard_billet_container_interface_temperature_c(470.0, 430.0)
    cold_to_hot = sheppard_billet_container_interface_temperature_c(470.0, 480.0)

    assert 430.0 < hot_to_cold < 470.0
    assert 470.0 < cold_to_hot < 480.0


def test_sheppard_interface_temperature_does_not_imply_friction_heat_partition():
    value = sheppard_billet_container_interface_temperature_c(470.0, 430.0)

    assert isinstance(value, float)
