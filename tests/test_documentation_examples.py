import math

from pyextrusion.economics import (
    BasicCostSpec,
    EconomicProductionBasis,
    calculate_basic_economics,
)
from pyextrusion.engineering import (
    AA6060,
    AA6063,
    axisymmetric_pressure_breakdown,
    breakthrough_pressure_increment_mpa_from_log_z,
    check_force_capacity,
    flow_stress_mpa,
    log_zener_hollomon_parameter,
    modified_feltham_mean_strain_rate_s_1,
    saha_complete_sticking_thermal_source_terms,
    sheppard_billet_container_interface_temperature_c,
    stuwe_surface_exit_temperature_estimate,
)


def test_documented_mechanical_screening_chain() -> None:
    ram_speed_mm_s = 0.70
    container_diameter_mm = 210.0
    extrusion_ratio = 40.0
    billet_temperature_c = 470.0

    strain_rate = modified_feltham_mean_strain_rate_s_1(
        ram_speed_mm_s,
        container_diameter_mm,
        extrusion_ratio,
    )
    ln_z = log_zener_hollomon_parameter(
        strain_rate,
        billet_temperature_c,
        AA6063,
    )
    flow_stress = flow_stress_mpa(
        strain_rate,
        billet_temperature_c,
        AA6063,
    )
    breakthrough = breakthrough_pressure_increment_mpa_from_log_z(
        ln_z,
        AA6063,
    )
    pressure = axisymmetric_pressure_breakdown(
        flow_stress_mpa=flow_stress,
        extrusion_ratio=extrusion_ratio,
        friction_factor_m=1.0,
        billet_contact_length_mm=800.0,
        container_diameter_mm=container_diameter_mm,
        breakthrough_increment_mpa=breakthrough,
    )
    screening = check_force_capacity(
        required_force_mn=pressure.required_force_mn,
        configured_force_limit_mn=35.0,
    )

    assert pressure.required_force_mn > 0.0
    assert screening.margin_mn == 35.0 - pressure.required_force_mn
    assert screening.within_limit

    for model in (AA6060, AA6063):
        assert flow_stress_mpa(0.30, 470.0, model) > 0.0


def test_documented_bounded_thermal_calls() -> None:
    stuwe = stuwe_surface_exit_temperature_estimate(
        billet_temperature_c=470.0,
        flow_stress_mpa=20.0,
        extrusion_ratio=40.0,
        ram_speed_mm_s=0.70,
        billet_contact_length_mm=800.0,
        exit_speed_m_min=28.0,
        die_land_length_mm=10.0,
    )
    saha = saha_complete_sticking_thermal_source_terms(
        flow_stress_mpa=20.0,
        mean_strain_rate_s_1=0.30,
        ram_speed_mm_s=0.70,
        exit_speed_m_min=28.0,
    )
    interface_temperature_c = sheppard_billet_container_interface_temperature_c(
        billet_temperature_c=470.0,
        container_temperature_c=430.0,
    )

    assert math.isfinite(stuwe.estimated_surface_exit_temperature_c)
    assert saha.deformation_heat_generation_w_m3 > 0.0
    assert 430.0 < interface_temperature_c < 470.0


def test_documented_economics_example() -> None:
    costs = BasicCostSpec(
        press_hour_cost=200.0,
        maintenance_hour_cost=20.0,
        labor_hour_cost=30.0,
        raw_material_cost_per_kg=3.0,
        scrap_processing_cost_per_kg=0.20,
        scrap_sale_value_per_kg=1.50,
        good_product_sale_value_per_kg=5.00,
        target_profit_margin_pct=20.0,
        die_cost=2000.0,
        extra_tooling_cost=500.0,
        die_trial_count=3,
        die_trial_cost_each=250.0,
        currency="EUR",
    )
    production = EconomicProductionBasis(
        production_time_h=2.0,
        good_kg_manufactured=900.0,
        revenue_good_kg=800.0,
        scrap_kg=100.0,
    )

    result = calculate_basic_economics(costs, production)

    assert result.recurring_cost > 0.0
    assert result.first_run_cost > result.recurring_cost
    assert result.target_value_per_kg_first_run > 0.0
