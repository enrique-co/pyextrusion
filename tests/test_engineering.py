import math

import pytest

from pyextrusion.engineering import (
    EnergyComparison,
    EngineeringResult,
    ForceCapacityCheck,
    HydraulicSystemSpec,
    Interval,
    PressEngineeringSpec,
    RamOperatingRange,
    SourceRef,
    SpecificEnergyBasis,
    check_force_capacity,
    check_press_force_capacity,
    circular_area_m2_from_diameter_mm,
    compare_specific_energy_kwh_per_tonne,
    energy_kwh_from_constant_power_kw,
    flow_l_min_from_area_m2_speed_mm_s,
    force_mn_from_specific_pressure_mpa,
    hydraulic_force_contribution_mn_from_pressure_bar,
    hydraulic_pressure_bar_from_force_contribution_mn,
    hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min,
    ram_power_kw_from_force_mn_speed_mm_s,
    ram_work_kwh_from_constant_force_mn_stroke_mm,
    specific_energy_kwh_per_tonne,
    specific_pressure_mpa_from_force_mn,
    true_strain_from_extrusion_ratio,
)


def test_circular_area_from_diameter_is_si_consistent():
    assert circular_area_m2_from_diameter_mm(200.0) == pytest.approx(math.pi * 0.2**2 / 4.0)


def test_specific_pressure_and_force_are_inverse_operations():
    pressure_mpa = specific_pressure_mpa_from_force_mn(10.0, 0.02)
    assert pressure_mpa == pytest.approx(500.0)
    assert force_mn_from_specific_pressure_mpa(pressure_mpa, 0.02) == pytest.approx(10.0)


def test_hydraulic_pressure_and_force_contribution_are_inverse_operations():
    force_mn = hydraulic_force_contribution_mn_from_pressure_bar(300.0, 0.5)
    assert force_mn == pytest.approx(15.0)
    assert hydraulic_pressure_bar_from_force_contribution_mn(force_mn, 0.5) == pytest.approx(300.0)


def test_hydraulic_primitives_describe_contributions_not_automatic_net_force():
    advance = hydraulic_force_contribution_mn_from_pressure_bar(300.0, 0.5)
    opposing = hydraulic_force_contribution_mn_from_pressure_bar(50.0, 0.3)
    net_from_explicit_balance = advance - opposing

    assert advance == pytest.approx(15.0)
    assert opposing == pytest.approx(1.5)
    assert net_from_explicit_balance == pytest.approx(13.5)
    # Inverting a net force as if it were the advance-chamber contribution does
    # not recover the actual advance pressure. This protects the API contract.
    assert hydraulic_pressure_bar_from_force_contribution_mn(net_from_explicit_balance, 0.5) == pytest.approx(270.0)


def test_zero_force_and_pressure_are_valid_states_with_positive_area():
    assert specific_pressure_mpa_from_force_mn(0.0, 0.02) == pytest.approx(0.0)
    assert force_mn_from_specific_pressure_mpa(0.0, 0.02) == pytest.approx(0.0)
    assert hydraulic_force_contribution_mn_from_pressure_bar(0.0, 0.5) == pytest.approx(0.0)
    assert hydraulic_pressure_bar_from_force_contribution_mn(0.0, 0.5) == pytest.approx(0.0)


def test_true_strain_uses_natural_logarithm():
    assert true_strain_from_extrusion_ratio(1.0) == pytest.approx(0.0)
    assert true_strain_from_extrusion_ratio(math.e**2) == pytest.approx(2.0)


@pytest.mark.parametrize(
    "call",
    [
        lambda: circular_area_m2_from_diameter_mm(0.0),
        lambda: circular_area_m2_from_diameter_mm(float("inf")),
        lambda: circular_area_m2_from_diameter_mm("200"),
        lambda: specific_pressure_mpa_from_force_mn(-1.0, 0.02),
        lambda: specific_pressure_mpa_from_force_mn(True, 0.02),
        lambda: force_mn_from_specific_pressure_mpa(500.0, 0.0),
        lambda: hydraulic_force_contribution_mn_from_pressure_bar(-1.0, 0.5),
        lambda: hydraulic_pressure_bar_from_force_contribution_mn(10.0, float("nan")),
        lambda: flow_l_min_from_area_m2_speed_mm_s(0.0, 10.0),
        lambda: true_strain_from_extrusion_ratio(0.99),
        lambda: true_strain_from_extrusion_ratio(float("nan")),
        lambda: true_strain_from_extrusion_ratio("40"),
    ],
)
def test_engineering_primitives_reject_invalid_inputs(call):
    with pytest.raises(ValueError):
        call()


def test_engineering_metadata_keeps_bounds_text_and_provenance():
    source = SourceRef(
        source_kind="documented",
        reference="manufacturer datasheet",
        detail="nominal operating condition",
    )
    result = EngineeringResult(
        value=12.5,
        unit="MN",
        estimate_kind="derived",
        confidence="high",
        uncertainty=Interval(12.0, 13.0),
        assumptions=("ideal axial force conversion",),
        warnings=("configured limit only",),
        provenance=(source,),
    )

    data = result.to_dict()
    assert data["value"] == pytest.approx(12.5)
    assert data["unit"] == "MN"
    assert data["uncertainty"] == {"lower": 12.0, "upper": 13.0}
    assert data["assumptions"] == ("ideal axial force conversion",)
    assert data["warnings"] == ("configured limit only",)
    assert data["provenance"][0]["source_kind"] == "documented"


def test_uncertainty_interval_is_absolute_and_must_contain_result_value():
    with pytest.raises(ValueError, match="must lie within"):
        EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="low",
            uncertainty=Interval(0.1, 0.2),
        )


def test_unavailable_result_requires_an_explicit_reason():
    result = EngineeringResult(
        value=None,
        unit="MN",
        estimate_kind="indicator",
        confidence="low",
        unavailable_reason="required machine input not supplied",
    )
    assert result.to_dict()["unavailable_reason"] == "required machine input not supplied"

    with pytest.raises(ValueError, match="requires a non-empty unavailable_reason"):
        EngineeringResult(value=None, unit="MN", estimate_kind="indicator", confidence="low")


def test_invalid_interval_is_rejected():
    with pytest.raises(ValueError):
        Interval(2.0, 1.0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Interval("1", 2.0),
        lambda: Interval(False, 2.0),
        lambda: EngineeringResult(
            value="12.5",
            unit="MN",
            estimate_kind="derived",
            confidence="high",
        ),
        lambda: EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="high",
            uncertainty={"lower": 12.0, "upper": 13.0},
        ),
        lambda: EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="high",
            provenance=({"source_kind": "fabricated", "reference": ""},),
        ),
        lambda: EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="high",
            assumptions="piston only",
        ),
        lambda: EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="high",
            warnings=(False,),
        ),
        lambda: EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="high",
            assumptions=("",),
        ),
        lambda: EngineeringResult(
            value=12.5,
            unit="MN",
            estimate_kind="derived",
            confidence="high",
            unavailable_reason="not available",
        ),
    ],
)
def test_engineering_metadata_rejects_untyped_or_malformed_values(factory):
    with pytest.raises(ValueError):
        factory()


def test_press_engineering_spec_stores_only_explicit_machine_data():
    source = SourceRef(source_kind="documented", reference="press datasheet")
    ram_range = RamOperatingRange(minimum_mm_s=0.0, maximum_mm_s=20.0)
    hydraulics = HydraulicSystemSpec(
        pressure_force_area_m2=0.5,
        max_pressure_bar=300.0,
        max_flow_l_min=1200.0,
        installed_power_kw=500.0,
        installed_power_kind="motor_shaft",
        provenance=(source,),
    )
    press = PressEngineeringSpec(
        press_id="P-X",
        container_diameter_mm=236.0,
        rated_force_mn=35.0,
        operating_force_limit_mn=33.0,
        ram_speed_range=ram_range,
        hydraulic_system=hydraulics,
        provenance=(source,),
    )

    assert press.container_area_m2 == pytest.approx(math.pi * 0.236**2 / 4.0)
    assert press.configured_force_limit_mn == pytest.approx(33.0)
    assert press.configured_force_limit_source == "operating_force_limit"
    assert press.ram_speed_range.contains(10.0)
    assert not press.ram_speed_range.contains(21.0)
    assert press.hydraulic_system.max_pressure_bar == pytest.approx(300.0)
    assert press.hydraulic_system.pressure_force_area_m2 == pytest.approx(0.5)
    assert press.hydraulic_system.installed_power_kind == "motor_shaft"
    assert press.to_dict()["provenance"][0]["source_kind"] == "documented"


def test_press_force_limit_falls_back_to_rated_force_without_derating():
    press = PressEngineeringSpec(
        press_id="P-X",
        container_diameter_mm=210.0,
        rated_force_mn=25.0,
    )
    assert press.configured_force_limit_mn == pytest.approx(25.0)
    assert press.configured_force_limit_source == "rated_force"


def test_force_capacity_check_is_a_direct_configured_limit_comparison_only():
    result = check_force_capacity(required_force_mn=10.0, configured_force_limit_mn=12.0)
    assert result.configured_force_limit_mn == pytest.approx(12.0)
    assert result.limit_source == "caller_supplied"
    assert result.margin_mn == pytest.approx(2.0)
    assert result.utilization == pytest.approx(10.0 / 12.0)
    assert result.within_limit is True

    overloaded = check_force_capacity(required_force_mn=13.0, configured_force_limit_mn=12.0)
    assert overloaded.margin_mn == pytest.approx(-1.0)
    assert overloaded.within_limit is False


def test_force_capacity_equality_is_inside_scalar_limit_with_zero_margin():
    result = check_force_capacity(required_force_mn=12.0, configured_force_limit_mn=12.0)
    assert result.margin_mn == pytest.approx(0.0)
    assert result.utilization == pytest.approx(1.0)
    assert result.within_limit is True


def test_force_capacity_derived_fields_cannot_be_constructed_contradictorily():
    result = ForceCapacityCheck(13.0, 12.0)
    assert result.margin_mn == pytest.approx(-1.0)
    assert result.utilization == pytest.approx(13.0 / 12.0)
    assert result.within_limit is False
    assert result.to_dict()["within_limit"] is False


def test_press_capacity_check_preserves_operating_limit_origin():
    press = PressEngineeringSpec(
        press_id="P-X",
        container_diameter_mm=236.0,
        rated_force_mn=35.0,
        operating_force_limit_mn=33.0,
    )
    result = check_press_force_capacity(32.0, press)
    assert result.configured_force_limit_mn == pytest.approx(33.0)
    assert result.limit_source == "operating_force_limit"
    assert result.margin_mn == pytest.approx(1.0)


def test_press_capacity_check_requires_a_configured_force_limit():
    press = PressEngineeringSpec(press_id="P-X", container_diameter_mm=236.0)
    with pytest.raises(ValueError, match="no configured force limit"):
        check_press_force_capacity(10.0, press)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RamOperatingRange(minimum_mm_s=5.0, maximum_mm_s=4.0),
        lambda: RamOperatingRange(minimum_mm_s="1", maximum_mm_s=4.0),
        lambda: HydraulicSystemSpec(max_pressure_bar=True),
        lambda: HydraulicSystemSpec(installed_power_kw=500.0),
        lambda: HydraulicSystemSpec(installed_power_kind="motor_shaft"),
        lambda: HydraulicSystemSpec(provenance=({"source_kind": "documented", "reference": "x"},)),
        lambda: PressEngineeringSpec(press_id="", container_diameter_mm=236.0),
        lambda: PressEngineeringSpec(press_id="P-X", container_diameter_mm="236"),
        lambda: PressEngineeringSpec(
            press_id="P-X",
            container_diameter_mm=236.0,
            rated_force_mn=30.0,
            operating_force_limit_mn=31.0,
        ),
        lambda: PressEngineeringSpec(
            press_id="P-X",
            container_diameter_mm=236.0,
            ram_speed_range={"minimum_mm_s": 0.0, "maximum_mm_s": 20.0},
        ),
        lambda: check_force_capacity(True, 12.0),
        lambda: check_force_capacity(10.0, 0.0),
        lambda: ForceCapacityCheck(10.0, 12.0, "fabricated"),
    ],
)
def test_press_engineering_configuration_rejects_ambiguous_or_invalid_inputs(factory):
    with pytest.raises(ValueError):
        factory()


def test_pressure_flow_power_uses_pq_identity_with_explicit_units():
    assert hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min(300.0, 1200.0) == pytest.approx(600.0)
    assert hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min(0.0, 1200.0) == pytest.approx(0.0)


def test_single_boundary_qav_fpa_and_power_identities_are_cross_consistent():
    area_m2 = 0.5
    speed_mm_s = 10.0
    pressure_bar = 300.0

    flow_l_min = flow_l_min_from_area_m2_speed_mm_s(area_m2, speed_mm_s)
    force_mn = hydraulic_force_contribution_mn_from_pressure_bar(pressure_bar, area_m2)
    pressure_flow_power_kw = hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min(
        pressure_bar,
        flow_l_min,
    )
    mechanical_power_kw = ram_power_kw_from_force_mn_speed_mm_s(force_mn, speed_mm_s)

    assert flow_l_min == pytest.approx(300.0)
    assert force_mn == pytest.approx(15.0)
    assert pressure_flow_power_kw == pytest.approx(150.0)
    assert mechanical_power_kw == pytest.approx(150.0)
    assert pressure_flow_power_kw == pytest.approx(mechanical_power_kw)


def test_ram_power_uses_force_times_speed_identity():
    assert ram_power_kw_from_force_mn_speed_mm_s(33.0, 10.0) == pytest.approx(330.0)
    assert ram_power_kw_from_force_mn_speed_mm_s(33.0, 0.0) == pytest.approx(0.0)


def test_constant_power_energy_and_constant_force_work_are_consistent():
    force_mn = 10.0
    speed_mm_s = 5.0
    duration_s = 20.0
    stroke_mm = speed_mm_s * duration_s

    power_kw = ram_power_kw_from_force_mn_speed_mm_s(force_mn, speed_mm_s)
    energy_from_power = energy_kwh_from_constant_power_kw(power_kw, duration_s)
    energy_from_work = ram_work_kwh_from_constant_force_mn_stroke_mm(force_mn, stroke_mm)

    assert power_kw == pytest.approx(50.0)
    assert energy_from_power == pytest.approx(50.0 * 20.0 / 3600.0)
    assert energy_from_work == pytest.approx(energy_from_power)


def test_specific_energy_normalizes_only_the_supplied_energy_and_mass():
    assert specific_energy_kwh_per_tonne(10.0, 500.0) == pytest.approx(20.0)
    assert specific_energy_kwh_per_tonne(1000.0, 800.0) == pytest.approx(1250.0)
    assert specific_energy_kwh_per_tonne(1000.0, 1000.0) == pytest.approx(1000.0)


def test_specific_energy_comparison_requires_one_shared_declared_basis():
    basis = SpecificEnergyBasis(
        energy_boundary="hydraulic fluid at declared boundary",
        mass_basis="net produced mass",
        period_basis="same production scope",
    )
    result = compare_specific_energy_kwh_per_tonne(20.0, 18.0, basis=basis)
    assert result.reference_kwh_per_t == pytest.approx(20.0)
    assert result.candidate_kwh_per_t == pytest.approx(18.0)
    assert result.delta_kwh_per_t == pytest.approx(-2.0)
    assert result.candidate_to_reference_ratio == pytest.approx(0.9)
    assert result.to_dict()["basis"]["mass_basis"] == "net produced mass"


def test_energy_comparison_derived_fields_cannot_be_supplied_inconsistently():
    basis = SpecificEnergyBasis("ram mechanical", "gross product", "same batch")
    result = EnergyComparison(20.0, 18.0, basis)
    assert result.delta_kwh_per_t == pytest.approx(-2.0)
    assert result.candidate_to_reference_ratio == pytest.approx(0.9)


@pytest.mark.parametrize(
    "call",
    [
        lambda: hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min(-1.0, 1200.0),
        lambda: hydraulic_pressure_flow_power_kw_from_pressure_bar_flow_l_min(300.0, "1200"),
        lambda: ram_power_kw_from_force_mn_speed_mm_s(True, 10.0),
        lambda: ram_power_kw_from_force_mn_speed_mm_s(10.0, float("nan")),
        lambda: energy_kwh_from_constant_power_kw(10.0, -1.0),
        lambda: ram_work_kwh_from_constant_force_mn_stroke_mm(10.0, -1.0),
        lambda: specific_energy_kwh_per_tonne(10.0, 0.0),
        lambda: compare_specific_energy_kwh_per_tonne(
            20.0,
            18.0,
            basis="same",
        ),
        lambda: SpecificEnergyBasis("", "net mass", "same batch"),
    ],
)
def test_power_and_energy_identities_reject_invalid_or_ambiguous_inputs(call):
    with pytest.raises(ValueError):
        call()


def test_extreme_finite_inputs_cannot_silently_produce_nonfinite_results():
    assert specific_energy_kwh_per_tonne(1e308, 1e308) == pytest.approx(1000.0)
    with pytest.raises(ValueError, match="finite range"):
        check_force_capacity(1.0, 1e-309)
    with pytest.raises(ValueError, match="finite range"):
        circular_area_m2_from_diameter_mm(1e-200)
