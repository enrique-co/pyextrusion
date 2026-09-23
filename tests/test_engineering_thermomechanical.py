import pytest

from pyextrusion.engineering import (
    AA6060_VERLINDEN_1993,
    AA6063DirectExtrusionOperationEstimate,
    aa6063_direct_extrusion_operation_estimate,
)


def test_aa6063_direct_operation_composes_validated_components_for_one_point():
    result = aa6063_direct_extrusion_operation_estimate(
        billet_temperature_c=470.0,
        billet_diameter_mm=228.0,
        billet_length_mm=1300.0,
        container_diameter_mm=236.0,
        extrusion_ratio=31.2,
        ram_speed_mm_s=11.75,
        friction_factor_m=0.88,
        die_land_length_mm=5.0,
    )

    assert isinstance(result, AA6063DirectExtrusionOperationEstimate)
    assert result.equivalent_extrudate_diameter_mm == pytest.approx(42.2507775683)
    assert result.deformation_semiangle_deg == pytest.approx(62.4388848542)
    assert result.exit_speed_m_min == pytest.approx(21.996)
    assert result.billet_contact_length_mm == pytest.approx(1213.358230393565)
    assert result.mean_strain_rate_s_1 == pytest.approx(3.78221803913)
    assert result.ln_zener_hollomon == pytest.approx(24.2402200035)
    assert result.zener_hollomon_s_1 == pytest.approx(3.36816832726e10)
    assert result.flow_stress_mpa == pytest.approx(28.1793602855)
    assert result.breakthrough_increment_mpa == pytest.approx(14.0607735525)

    pressure = result.pressure_breakdown
    assert pressure.deformation_pressure_mpa == pytest.approx(185.14340331820532)
    assert pressure.container_friction_pressure_mpa == pytest.approx(294.43552147462833)
    assert pressure.peak_pressure_mpa == pytest.approx(493.63969834529735)
    assert pressure.required_force_mn == pytest.approx(21.593545969198164)

    thermal = result.surface_exit_temperature_estimate
    assert thermal.deformation_temperature_rise_c == pytest.approx(18.789831490367444)
    assert thermal.container_wall_temperature_rise_c == pytest.approx(19.847075222175725)
    assert thermal.die_land_temperature_rise_c == pytest.approx(7.116464746619617)
    assert thermal.estimated_surface_exit_temperature_c == pytest.approx(515.7533714591628)

    assert result.peak_pressure_mpa == pytest.approx(pressure.peak_pressure_mpa)
    assert result.required_force_mn == pytest.approx(pressure.required_force_mn)
    assert result.estimated_surface_exit_temperature_c == pytest.approx(
        thermal.estimated_surface_exit_temperature_c
    )


def test_aa6063_direct_operation_keeps_scope_and_limitations_visible():
    result = aa6063_direct_extrusion_operation_estimate(
        billet_temperature_c=470.0,
        billet_diameter_mm=228.0,
        billet_length_mm=1300.0,
        container_diameter_mm=236.0,
        extrusion_ratio=31.2,
        ram_speed_mm_s=11.75,
        friction_factor_m=0.88,
        die_land_length_mm=5.0,
    )

    text = " ".join(result.limitations)
    assert result.model_scope == "aa6063_equivalent_axisymmetric_direct_extrusion_single_operation_point"
    assert "porthole" in text
    assert "bridge-die" in text
    assert "Integral Profile" in text
    assert result.provenance[0].source_kind == "derived"

    data = result.to_dict()
    assert data["pressure_breakdown"]["model_scope"] == "axisymmetric_equivalent_direct_extrusion"
    assert (
        data["surface_exit_temperature_estimate"]["model_scope"]
        == "stuwe_three_component_surface_exit_estimate"
    )
    assert data["estimated_surface_exit_temperature_c"] == pytest.approx(
        result.estimated_surface_exit_temperature_c
    )


def test_aa6063_direct_operation_rejects_non_aa6063_constitutive_model():
    with pytest.raises(ValueError, match="limited to AA6063"):
        AA6063DirectExtrusionOperationEstimate(
            billet_temperature_c=470.0,
            billet_diameter_mm=228.0,
            billet_length_mm=1300.0,
            container_diameter_mm=236.0,
            extrusion_ratio=31.2,
            ram_speed_mm_s=11.75,
            friction_factor_m=0.88,
            die_land_length_mm=5.0,
            constitutive_model=AA6060_VERLINDEN_1993,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"billet_temperature_c": -273.15},
        {"billet_diameter_mm": 237.0},
        {"billet_length_mm": 0.0},
        {"container_diameter_mm": 0.0},
        {"extrusion_ratio": 1.0},
        {"extrusion_ratio": 100.0001},
        {"ram_speed_mm_s": 0.0},
        {"friction_factor_m": -0.01},
        {"friction_factor_m": 1.01},
        {"die_land_length_mm": -0.01},
    ],
)
def test_aa6063_direct_operation_rejects_invalid_or_out_of_scope_inputs(kwargs):
    base = {
        "billet_temperature_c": 470.0,
        "billet_diameter_mm": 228.0,
        "billet_length_mm": 1300.0,
        "container_diameter_mm": 236.0,
        "extrusion_ratio": 31.2,
        "ram_speed_mm_s": 11.75,
        "friction_factor_m": 0.88,
        "die_land_length_mm": 5.0,
    }
    base.update(kwargs)

    with pytest.raises(ValueError):
        aa6063_direct_extrusion_operation_estimate(**base)
