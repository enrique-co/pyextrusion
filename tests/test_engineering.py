import math

import pytest

from pyextrusion.engineering import (
    EngineeringResult,
    Interval,
    SourceRef,
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
