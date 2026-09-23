import math

import pytest

from pyextrusion.engineering import (
    AA6060_VERLINDEN_1993,
    AA6063_SHEPPARD_1999,
    HotWorkingConstitutiveModel,
    SourceRef,
    equivalent_extrudate_diameter_mm,
    flow_stress_mpa,
    log_zener_hollomon_parameter,
    modified_feltham_mean_strain_rate_s_1,
    sheppard_deformation_semiangle_deg,
    steady_state_flow_stress_mpa,
    zener_hollomon_parameter_s_1,
)


def test_sheppard_aa6063_constants_match_table_4_1():
    model = AA6063_SHEPPARD_1999

    assert model.alloy == "AA6063"
    assert model.alpha_mpa_inv == pytest.approx(0.040)
    assert model.n == pytest.approx(5.385)
    assert model.activation_energy_j_mol == pytest.approx(141_550.0)
    assert model.gas_constant_j_mol_k == pytest.approx(8.314)
    assert model.ln_A == pytest.approx(22.5)
    assert model.A_s_1 == pytest.approx(math.exp(22.5))
    assert model.provenance[0].source_kind == "literature"
    assert "Table 4.1" in model.provenance[0].reference


def test_verlinden_aa6060_constants_match_reported_hot_torsion_set():
    model = AA6060_VERLINDEN_1993

    assert model.alloy == "AA6060"
    assert model.alpha_mpa_inv == pytest.approx(0.035)
    assert model.n == pytest.approx(4.67)
    assert model.activation_energy_j_mol == pytest.approx(161_000.0)
    assert model.gas_constant_j_mol_k == pytest.approx(8.314)
    assert model.A_s_1 == pytest.approx(7.6301e10)
    assert model.ln_A == pytest.approx(math.log(7.6301e10))
    assert len(model.provenance) == 2
    assert "Verlinden" in model.provenance[0].reference
    assert "Sariyarlioglu" in model.provenance[1].reference


def test_aa6060_model_keeps_material_state_limitation_explicit():
    assert any("does not infer" in note or "does not" in note for note in AA6060_VERLINDEN_1993.notes)
    assert AA6060_VERLINDEN_1993.temperature_range_c is None
    assert AA6060_VERLINDEN_1993.mean_strain_rate_range_s_1 is None


def test_constitutive_model_does_not_imply_an_aa6060_alias():
    assert AA6063_SHEPPARD_1999.alloy == "AA6063"
    assert any("No automatic substitution for AA6060" in note for note in AA6063_SHEPPARD_1999.notes)


def test_equivalent_extrudate_diameter_preserves_area_ratio():
    diameter = equivalent_extrudate_diameter_mm(236.0, 31.2)

    assert diameter == pytest.approx(42.2507775683)
    assert (236.0 / diameter) ** 2 == pytest.approx(31.2)


def test_sheppard_deformation_semiangle_uses_natural_logarithm():
    angle = sheppard_deformation_semiangle_deg(31.2)

    assert angle == pytest.approx(62.4388848542)


def test_modified_feltham_mean_strain_rate_regression_case():
    strain_rate = modified_feltham_mean_strain_rate_s_1(
        ram_speed_mm_s=11.75,
        container_diameter_mm=236.0,
        extrusion_ratio=31.2,
    )

    assert strain_rate == pytest.approx(3.78221803913)


def test_modified_feltham_allows_explicit_semiangle_without_silent_correction():
    default_rate = modified_feltham_mean_strain_rate_s_1(11.75, 236.0, 31.2)
    explicit_rate = modified_feltham_mean_strain_rate_s_1(
        11.75,
        236.0,
        31.2,
        deformation_semiangle_deg=45.0,
    )

    assert explicit_rate < default_rate


def test_zener_hollomon_and_flow_stress_regression_for_aa6063():
    strain_rate = modified_feltham_mean_strain_rate_s_1(11.75, 236.0, 31.2)

    ln_z = log_zener_hollomon_parameter(strain_rate, 470.0, AA6063_SHEPPARD_1999)
    z_value = zener_hollomon_parameter_s_1(strain_rate, 470.0, AA6063_SHEPPARD_1999)
    stress = flow_stress_mpa(strain_rate, 470.0, AA6063_SHEPPARD_1999)

    assert ln_z == pytest.approx(24.2402200035)
    assert z_value == pytest.approx(3.36816832726e10)
    assert stress == pytest.approx(28.1793602855)
    assert steady_state_flow_stress_mpa(z_value, AA6063_SHEPPARD_1999) == pytest.approx(stress)


def test_zener_hollomon_and_flow_stress_regression_for_aa6060():
    strain_rate = modified_feltham_mean_strain_rate_s_1(11.75, 236.0, 31.2)

    ln_z = log_zener_hollomon_parameter(strain_rate, 470.0, AA6060_VERLINDEN_1993)
    stress = flow_stress_mpa(strain_rate, 470.0, AA6060_VERLINDEN_1993)

    assert ln_z == pytest.approx(27.3882082585)
    assert stress == pytest.approx(36.3902212867)


def test_flow_stress_increases_with_strain_rate_at_constant_temperature():
    low = flow_stress_mpa(1.0, 470.0, AA6063_SHEPPARD_1999)
    high = flow_stress_mpa(10.0, 470.0, AA6063_SHEPPARD_1999)

    assert high > low


def test_flow_stress_decreases_with_temperature_at_constant_strain_rate():
    cold = flow_stress_mpa(5.0, 430.0, AA6063_SHEPPARD_1999)
    hot = flow_stress_mpa(5.0, 500.0, AA6063_SHEPPARD_1999)

    assert hot < cold


def test_zero_ram_speed_is_a_valid_kinematic_state_but_not_a_hot_working_state():
    strain_rate = modified_feltham_mean_strain_rate_s_1(0.0, 236.0, 31.2)
    assert strain_rate == pytest.approx(0.0)

    with pytest.raises(ValueError):
        zener_hollomon_parameter_s_1(strain_rate, 470.0, AA6063_SHEPPARD_1999)


@pytest.mark.parametrize(
    "call",
    [
        lambda: equivalent_extrudate_diameter_mm(0.0, 30.0),
        lambda: equivalent_extrudate_diameter_mm(236.0, 1.0),
        lambda: sheppard_deformation_semiangle_deg(1.0),
        lambda: modified_feltham_mean_strain_rate_s_1(-1.0, 236.0, 30.0),
        lambda: modified_feltham_mean_strain_rate_s_1(10.0, 236.0, 30.0, deformation_semiangle_deg=90.0),
        lambda: modified_feltham_mean_strain_rate_s_1(True, 236.0, 30.0),
        lambda: zener_hollomon_parameter_s_1(1.0, -273.15, AA6063_SHEPPARD_1999),
        lambda: zener_hollomon_parameter_s_1(0.0, 470.0, AA6063_SHEPPARD_1999),
        lambda: steady_state_flow_stress_mpa(0.0, AA6063_SHEPPARD_1999),
        lambda: flow_stress_mpa(1.0, 470.0, "AA6063"),
    ],
)
def test_phase1_equations_reject_invalid_or_ambiguous_inputs(call):
    with pytest.raises(ValueError):
        call()


def test_constitutive_model_rejects_malformed_inputs_and_untyped_provenance():
    with pytest.raises(ValueError):
        HotWorkingConstitutiveModel(
            alloy="",
            alpha_mpa_inv=0.04,
            n=5.0,
            activation_energy_j_mol=140_000.0,
            ln_A=22.0,
        )

    with pytest.raises(ValueError):
        HotWorkingConstitutiveModel(
            alloy="AA6063",
            alpha_mpa_inv=0.0,
            n=5.0,
            activation_energy_j_mol=140_000.0,
            ln_A=22.0,
        )

    with pytest.raises(ValueError):
        HotWorkingConstitutiveModel(
            alloy="AA6063",
            alpha_mpa_inv=0.04,
            n=5.0,
            activation_energy_j_mol=140_000.0,
            ln_A=22.0,
            provenance=({"source_kind": "literature", "reference": "x"},),
        )


def test_custom_constitutive_model_preserves_explicit_literature_source():
    source = SourceRef(
        source_kind="literature",
        reference="independent hot-working study",
        detail="caller-supplied constants",
    )
    model = HotWorkingConstitutiveModel(
        alloy="TEST",
        alpha_mpa_inv=0.03,
        n=4.0,
        activation_energy_j_mol=150_000.0,
        ln_A=20.0,
        provenance=(source,),
    )

    assert model.provenance == (source,)
    assert model.to_dict()["provenance"][0]["source_kind"] == "literature"
