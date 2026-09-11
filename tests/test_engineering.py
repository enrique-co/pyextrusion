import math

import pytest

from pyextrusion.engineering import (
    EngineeringResult,
    HydraulicSystemSpec,
    Interval,
    PressEngineeringSpec,
    RamOperatingRange,
    SourceRef,
    check_force_capacity,
    check_press_force_capacity,
    circular_area_m2_from_diameter_mm,
    force_mn_from_specific_pressure_mpa,
    hydraulic_force_mn_from_pressure_bar,
    hydraulic_pressure_bar_from_force_mn,
    specific_pressure_mpa_from_force_mn,
    true_strain_from_extrusion_ratio,
)


def test_circular_area_from_diameter_is_si_consistent():
    assert circular_area_m2_from_diameter_mm(200.0) == pytest.approx(math.pi * 0.2**2 / 4.0)


def test_specific_pressure_and_force_are_inverse_operations():
    pressure_mpa = specific_pressure_mpa_from_force_mn(10.0, 0.02)
    assert pressure_mpa == pytest.approx(500.0)
    assert force_mn_from_specific_pressure_mpa(pressure_mpa, 0.02) == pytest.approx(10.0)


def test_hydraulic_pressure_and_force_are_inverse_operations():
    force_mn = hydraulic_force_mn_from_pressure_bar(300.0, 0.5)
    assert force_mn == pytest.approx(15.0)
    assert hydraulic_pressure_bar_from_force_mn(force_mn, 0.5) == pytest.approx(300.0)


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
        lambda: hydraulic_force_mn_from_pressure_bar(0.0, 0.5),
        lambda: hydraulic_pressure_bar_from_force_mn(10.0, float("nan")),
        lambda: true_strain_from_extrusion_ratio(0.99),
        lambda: true_strain_from_extrusion_ratio(float("nan")),
        lambda: true_strain_from_extrusion_ratio("40"),
    ],
)
def test_engineering_primitives_reject_invalid_inputs(call):
    with pytest.raises(ValueError):
        call()


def test_engineering_metadata_keeps_uncertainty_and_provenance():
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
        provenance=(source,),
    )

    data = result.to_dict()
    assert data["value"] == pytest.approx(12.5)
    assert data["unit"] == "MN"
    assert data["uncertainty"] == {"lower": 12.0, "upper": 13.0}
    assert data["provenance"][0]["source_kind"] == "documented"


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
    ],
)
def test_engineering_metadata_rejects_untyped_or_malformed_values(factory):
    with pytest.raises(ValueError):
        factory()


def test_press_engineering_spec_stores_only_explicit_machine_data():
    source = SourceRef(source_kind="documented", reference="press datasheet")
    ram_range = RamOperatingRange(minimum_mm_s=0.0, maximum_mm_s=20.0)
    hydraulics = HydraulicSystemSpec(
        effective_area_m2=0.5,
        max_pressure_bar=300.0,
        max_flow_l_min=1200.0,
        installed_power_kw=500.0,
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
    assert press.ram_speed_range.contains(10.0)
    assert not press.ram_speed_range.contains(21.0)
    assert press.hydraulic_system.max_pressure_bar == pytest.approx(300.0)
    assert press.to_dict()["provenance"][0]["source_kind"] == "documented"


def test_press_force_limit_falls_back_to_rated_force_without_derating():
    press = PressEngineeringSpec(
        press_id="P-X",
        container_diameter_mm=210.0,
        rated_force_mn=25.0,
    )
    assert press.configured_force_limit_mn == pytest.approx(25.0)


def test_force_capacity_check_is_a_direct_comparison_only():
    result = check_force_capacity(required_force_mn=10.0, available_force_mn=12.0)
    assert result.margin_mn == pytest.approx(2.0)
    assert result.utilization == pytest.approx(10.0 / 12.0)
    assert result.within_limit is True

    overloaded = check_force_capacity(required_force_mn=13.0, available_force_mn=12.0)
    assert overloaded.margin_mn == pytest.approx(-1.0)
    assert overloaded.within_limit is False


def test_press_capacity_check_uses_explicit_operating_limit_when_present():
    press = PressEngineeringSpec(
        press_id="P-X",
        container_diameter_mm=236.0,
        rated_force_mn=35.0,
        operating_force_limit_mn=33.0,
    )
    result = check_press_force_capacity(32.0, press)
    assert result.available_force_mn == pytest.approx(33.0)
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
    ],
)
def test_press_engineering_configuration_rejects_ambiguous_or_invalid_inputs(factory):
    with pytest.raises(ValueError):
        factory()
