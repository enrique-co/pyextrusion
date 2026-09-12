import json
import sys
import pytest

from pyextrusion import (
    ButtRule, PressSpec, ProfileSpec, SawSpec, StudyInput,
    calculate, calculate_simple, extrusion_ratio, ram_speed, section_from_linear_weight,
    study_from_dict, validate_study,
)


def press():
    return PressSpec(
        name="Test Press", nominal_force_t=2500, container_diameter_mm=210, billet_diameter_mm=203,
        billet_area_m2_override=0.032365, billet_weight_kg_per_mm_override=0.087,
        billet_min_mm=400, billet_max_mm=1200, table_length_m=54, dead_time_sec=15,
        saws=SawSpec(4, 4, 4),
        butt_rules=(
            ButtRule("solid", 2.0, 20),
            ButtRule("solid", None, 25, min_total_linear_weight_kg_m=2.0),
            ButtRule("hollow", 2.5, 25),
            ButtRule("hollow", None, 30, min_total_linear_weight_kg_m=2.5),
        ),
    )


def test_section_from_linear_weight():
    assert section_from_linear_weight(1.5) == pytest.approx(1.5 / 2700)


def test_extrusion_ratio():
    assert extrusion_ratio(0.032365, 0.001) == pytest.approx(32.365)


def test_ram_speed_units():
    m_min, mm_s = ram_speed(24, 0.001, 0.032365)
    assert mm_s == pytest.approx(m_min * 1000 / 60)


def test_base_calculation_is_structured():
    data = StudyInput(
        press=press(), profile=ProfileSpec(1.35, 2, "solid"),
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000,
        front_scrap_m=2, complexity="normal",
    )
    r = calculate(data)
    assert r.theoretical_cuts == 7
    assert r.cuts >= 1
    assert r.bars_per_billet == r.cuts * 2
    assert r.extrusion_ratio > 0
    assert r.ram_speed_mm_s > 0
    assert len(r.configurations) == 2
    assert json.loads(r.to_json())["press_name"] == "Test Press"


def test_manual_cuts_are_respected_and_warned_if_infeasible():
    data = StudyInput(
        press=press(), profile=ProfileSpec(1.35, 2, "solid"),
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2, cuts=20,
    )
    r = calculate(data)
    assert r.cuts == 20
    assert not r.viable
    assert any("User-defined" in w for w in r.warnings)


def test_simple_api_matches_advanced_api():
    advanced = calculate(StudyInput(
        press=press(), profile=ProfileSpec(1.35, 2, "solid"),
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000,
        front_scrap_m=2,
    ))
    simple = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000, front_scrap_m=2,
    )
    assert simple.to_dict() == advanced.to_dict()


def test_press_density_is_used_for_profile_section_when_not_supplied():
    p = PressSpec(
        name="Density test", nominal_force_t=1000, container_diameter_mm=160, billet_diameter_mm=150,
        billet_min_mm=100, billet_max_mm=2000, table_length_m=20, dead_time_sec=5,
        aluminium_density_kg_m3=2800,
        butt_rules=(ButtRule("solid", None, 10),),
    )
    r = calculate_simple(
        p, linear_weight_kg_m=1.4, exits=1, profile_type="solid", exit_speed_m_min=10,
        cut_length_mm=1000, bars_requested=10,
    )
    assert r.profile_section_per_exit_m2 == pytest.approx(1.4 / 2800)


def test_json_schema_03_and_validation():
    d = {
        "schema_version": "0.3",
        "press": {
            "name": "JSON Press", "nominal_force_t": 2500, "container_diameter_mm": 210,
            "billet_diameter_mm": 203, "billet_min_mm": 400, "billet_max_mm": 1200,
            "table_length_m": 54, "dead_time_sec": 15,
            "butt_rules": [{"profile_type": "solid", "max_total_linear_weight_kg_m": None, "butt_mm": 25}],
        },
        "profile": {"linear_weight_kg_m": 1.35, "exits": 2, "profile_type": "solid"},
        "production": {
            "exit_speed_m_min": 24, "cut_length_mm": 7000, "bars_requested": 1000,
            "multi_billet_front_scrap_m": 1.0,
        },
    }
    study = study_from_dict(d)
    assert study.multi_billet_front_scrap_m == 1.0
    assert not [m for m in validate_study(study) if m.level == "error"]


def test_schema_02_remains_backward_compatible():
    d = {
        "schema_version": "0.2",
        "press": {
            "name": "JSON Press", "nominal_force_t": 2500, "container_diameter_mm": 210,
            "billet_diameter_mm": 203, "billet_min_mm": 400, "billet_max_mm": 1200,
            "table_length_m": 54, "dead_time_sec": 15,
            "butt_rules": [{"profile_type": "solid", "max_total_linear_weight_kg_m": None, "butt_mm": 25}],
        },
        "profile": {"linear_weight_kg_m": 1.35, "exits": 2, "profile_type": "solid"},
        "production": {"exit_speed_m_min": 24, "cut_length_mm": 7000, "bars_requested": 1000},
    }
    assert study_from_dict(d).multi_billet_front_scrap_m is None


def test_unsupported_schema_version_fails_clearly():
    with pytest.raises(ValueError, match="Unsupported schema_version"):
        study_from_dict({"schema_version": "9.9"})


def test_one_billet_two_profiles_has_first_priority_when_valid():
    r = calculate_simple(
        press(), linear_weight_kg_m=0.4, exits=1, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2,
    )
    assert "1_billet_2_profiles" in r.valid_configurations
    assert r.recommended_configuration == "1_billet_2_profiles"
    cfg = next(c for c in r.configurations if c.name == "1_billet_2_profiles")
    assert cfg.billet_length_mm == pytest.approx(2 * next(c for c in r.configurations if c.name == "1_billet_1_profile").billet_useful_length_mm + r.butt_mm)
    assert r.dead_time_events == (r.billets - 1) + r.billets


def test_double_profile_is_invalid_when_single_pull_exceeds_table():
    # Sequential double-profile production still requires each individual
    # physical pull, including downstream saw kerfs, to fit the runout table.
    p = press()
    r = calculate_simple(
        p, linear_weight_kg_m=0.30, exits=1, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2, cuts=8,
    )
    cfg = next(c for c in r.configurations if c.name == "1_billet_2_profiles")
    expected_physical_pull = (
        8 * 7.0 + 2.0
        + p.saws.puller_mm / 1000.0
        + (8 + 1) * p.saws.final_mm / 1000.0
    )
    assert cfg.table_occupancy_length_m == pytest.approx(expected_physical_pull)
    assert not cfg.valid
    assert "physical profile pull including saw kerfs exceeds table length" in cfg.reasons
    assert not r.viable
    assert r.recommended_configuration is None


def test_v21_billet_first_selection_can_prefer_double_profile_over_more_billets_per_pull():
    # The v2.1 rule optimizes billet length first. The one-profile family can
    # form a 3-billet continuous pull here, but the double-profile family
    # produces a longer valid billet and therefore wins.
    r = calculate_simple(
        press(), linear_weight_kg_m=5.0, exits=1, profile_type="solid",
        exit_speed_m_min=15, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2,
    )
    one = next(c for c in r.configurations if c.name == "k_billets_1_profile")
    double = next(c for c in r.configurations if c.name == "1_billet_2_profiles")
    assert one.valid
    assert one.billets_per_pull == 3
    assert double.valid
    assert double.billet_length_mm > one.billet_length_mm
    assert r.recommended_configuration == "1_billet_2_profiles"
    assert r.cuts == double.cuts


def test_multi_billet_front_scrap_recalculates_billet_geometry():
    p = press()
    r = calculate_simple(
        p, linear_weight_kg_m=4.0, exits=1, profile_type="solid",
        exit_speed_m_min=15, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2, multi_billet_front_scrap_m=1,
    )
    cfg = next(c for c in r.configurations if c.name == "k_billets_1_profile")
    nominal_segment = r.cuts * 7.0 + 1.0
    final_kerf_m = p.saws.final_mm / 1000.0
    shared_kerf_m = (p.saws.puller_mm + p.saws.final_mm) / 1000.0
    expected_physical_per_billet = (
        nominal_segment
        + r.cuts * final_kerf_m
        + shared_kerf_m / cfg.billets_per_pull
    )
    expected_useful = 4.0 * expected_physical_per_billet / 0.087
    assert cfg.length_per_billet_m == pytest.approx(expected_physical_per_billet)
    assert cfg.billet_useful_length_mm == pytest.approx(expected_useful)
    assert cfg.billet_length_mm == pytest.approx(expected_useful + r.butt_mm)
    assert cfg.total_configuration_length_m == pytest.approx(
        cfg.billets_per_pull * expected_physical_per_billet
    )
    assert cfg.billets_per_pull >= 2


def test_billet_ratio_uses_recommended_configuration_billet():
    r = calculate_simple(
        press(), linear_weight_kg_m=0.4, exits=1, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2,
    )
    assert r.recommended_configuration == "1_billet_2_profiles"
    assert r.billet_ratio == pytest.approx(r.billet_length_mm / press().billet_max_mm)


def test_v090_double_profile_uses_two_profiles_per_billet_for_bars():
    r = calculate_simple(
        press(), linear_weight_kg_m=0.4, exits=1, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2,
    )
    assert r.recommended_configuration == "1_billet_2_profiles"
    assert r.production.profiles_per_billet == 2
    assert r.bars_per_billet == r.cuts * 1 * 2
    assert r.billets == 8  # ceil(100 / 14)


def test_double_profile_uses_single_profile_table_occupancy():
    r = calculate_simple(
        press(), linear_weight_kg_m=0.4, exits=1, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2,
    )
    cfg = next(c for c in r.configurations if c.name == "1_billet_2_profiles")
    base = next(c for c in r.configurations if c.name == "1_billet_1_profile")
    assert cfg.total_configuration_length_m == pytest.approx(2 * base.length_per_billet_m)
    assert cfg.length_per_profile_m == pytest.approx(base.length_per_billet_m)
    assert cfg.table_occupancy_length_m == pytest.approx(base.length_per_billet_m)
    assert r.geometry.profile_pull_length_m == pytest.approx(base.length_per_billet_m)
    assert r.geometry.extruded_length_per_billet_m == pytest.approx(2 * base.length_per_billet_m)
    assert r.geometry.table_occupancy_length_m == pytest.approx(base.length_per_billet_m)
    assert r.table_ratio == pytest.approx(cfg.table_occupancy_length_m / press().table_length_m)


def test_case_api_matches_simple_api():
    from pyextrusion import ProductionSpec, StudyCase, calculate_case
    case = StudyCase(
        profile=ProfileSpec(1.35, 2, "solid"),
        production=ProductionSpec(
            exit_speed_m_min=24,
            cut_length_mm=7000,
            bars_requested=1000,
            front_scrap_m=2,
        ),
    )
    via_case = calculate_case(press(), case)
    via_simple = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000, front_scrap_m=2,
    )
    assert via_case.to_dict() == via_simple.to_dict()


def test_compare_presses_keeps_results_without_declaring_winner():
    from pyextrusion import ProductionSpec, StudyCase, compare_presses
    p2 = PressSpec(
        name="Second Press", nominal_force_t=3500, container_diameter_mm=236, billet_diameter_mm=228,
        billet_min_mm=500, billet_max_mm=1300, table_length_m=64, dead_time_sec=14,
        saws=SawSpec(5, 5, 4), butt_rules=(ButtRule("solid", None, 30),),
    )
    case = StudyCase(
        profile=ProfileSpec(1.35, 2, "solid"),
        production=ProductionSpec(24, 7000, 1000, front_scrap_m=2),
    )
    comparison = compare_presses([press(), p2], case)
    assert len(comparison.results) == 2
    assert comparison.results[0].press_name == "Test Press"
    assert comparison.results[1].press_name == "Second Press"
    assert "winner" not in comparison.to_dict()


def test_press_and_case_json_round_trip(tmp_path):
    from pyextrusion import (
        ProductionSpec, StudyCase, load_case_json, load_press_json,
        save_case_json, save_press_json,
    )
    case = StudyCase(
        profile=ProfileSpec(1.2, 2, "hollow"),
        production=ProductionSpec(18, 6500, 300, front_scrap_m=1.5, complexity="medium"),
    )
    press_path = tmp_path / "press.json"
    case_path = tmp_path / "case.json"
    save_press_json(press(), press_path)
    save_case_json(case, case_path)
    loaded_press = load_press_json(press_path)
    loaded_case = load_case_json(case_path)
    assert loaded_press == press()
    assert loaded_case == case
    assert json.loads(case_path.read_text())["schema_version"] == "1.1"


def test_schema_04_supports_case_without_embedded_press():
    from pyextrusion import case_from_dict
    d = {
        "schema_version": "0.4",
        "profile": {"linear_weight_kg_m": 1.1, "exits": 2, "profile_type": "solid"},
        "production": {"exit_speed_m_min": 20, "cut_length_mm": 6000, "bars_requested": 100},
    }
    case = case_from_dict(d)
    assert case.profile.exits == 2
    assert case.production.cut_length_mm == 6000


def test_human_reports_are_readable():
    from pyextrusion import ProductionSpec, StudyCase, compare_presses, format_comparison, format_press, format_result
    case = StudyCase(ProfileSpec(1.35, 2, "solid"), ProductionSpec(24, 7000, 100, front_scrap_m=2))
    r = calculate(case.to_study_input(press()))
    assert "Real net output" in format_result(r)
    assert "Billet range" in format_press(press())
    table = format_comparison(compare_presses([press(), press()], case))
    assert "Net kg/h" in table
    assert "does not make the final industrial decision" in table


def test_validate_case_is_press_independent():
    from pyextrusion import ProductionSpec, StudyCase, validate_case
    case = StudyCase(ProfileSpec(1.0, 1, "solid"), ProductionSpec(20, 6000, 10))
    assert not [m for m in validate_case(case) if m.level == "error"]



def test_annual_demand_normalization_from_kg():
    from pyextrusion import AnnualDemandSpec, normalize_annual_demand
    profile = ProfileSpec(2.0, 1, "solid")
    n = normalize_annual_demand(profile, 5000, AnnualDemandSpec("kg", 20000))
    assert n.kg_target == pytest.approx(20000)
    assert n.meters_target == pytest.approx(10000)
    assert n.bars_target == 2000


def test_annual_demand_normalization_from_metres_uses_ceil_bars():
    from pyextrusion import AnnualDemandSpec, normalize_annual_demand
    profile = ProfileSpec(1.5, 1, "solid")
    n = normalize_annual_demand(profile, 6000, AnnualDemandSpec("m", 100.1))
    assert n.meters_target == pytest.approx(100.1)
    assert n.kg_target == pytest.approx(150.15)
    assert n.bars_target == 17


def test_annual_demand_in_bars_requires_whole_bars():
    from pyextrusion import AnnualDemandSpec, InvalidAnnualDemandError, normalize_annual_demand
    profile = ProfileSpec(1.25, 1, "solid")
    with pytest.raises(InvalidAnnualDemandError) as exc:
        AnnualDemandSpec("bars", 10.2)
    assert exc.value.code == "PX1006"
    n = normalize_annual_demand(profile, 7000, AnnualDemandSpec("bars", 11))
    assert n.bars_target == 11
    assert n.meters_target == pytest.approx(77)
    assert n.kg_target == pytest.approx(96.25)


def test_annual_calculation_uses_normalized_bars_without_mutating_case():
    from pyextrusion import AnnualDemandSpec, ProductionSpec, StudyCase, calculate_annual_demand
    case = StudyCase(
        ProfileSpec(2.0, 1, "solid"),
        ProductionSpec(20, 5000, 10, front_scrap_m=1),
    )
    result = calculate_annual_demand(press(), case, AnnualDemandSpec("kg", 20000))
    assert case.production.bars_requested == 10
    assert result.normalized.bars_target == 2000
    assert result.calculation.good_kg_requested == pytest.approx(20000)
    assert result.billets_annual == result.calculation.billets
    assert result.hours_annual == pytest.approx(result.calculation.total_time_min / 60)


def test_annual_demand_json_round_trip(tmp_path):
    from pyextrusion import AnnualDemandSpec, load_annual_demand_json, save_annual_demand_json
    demand = AnnualDemandSpec("kg", 20000)
    path = tmp_path / "annual_demand.json"
    save_annual_demand_json(demand, path)
    assert load_annual_demand_json(path) == demand
    data = json.loads(path.read_text())
    assert data["schema_version"] == "1.1"
    assert data["annual_demand"]["unit"] == "kg"


def test_invalid_annual_demand_validation_is_strict_at_construction():
    from pyextrusion import AnnualDemandSpec, InvalidAnnualDemandError
    with pytest.raises(InvalidAnnualDemandError) as exc:
        AnnualDemandSpec("kg", 0)
    assert exc.value.code == "PX1006"


def test_public_project_metadata():
    import importlib.metadata
    import pyextrusion
    assert pyextrusion.__version__ == importlib.metadata.version("pyextrusion")
    assert pyextrusion.__author__ == "Enrique Calvo Ordonez"
    assert pyextrusion.__license__ == "Apache-2.0"
    assert pyextrusion.__url__ == "https://pyextrusion.com"


def test_cli_info_reports_identity(monkeypatch, capsys):
    import pyextrusion
    from pyextrusion.cli import main
    monkeypatch.setattr("sys.argv", ["pyextrusion", "info"])
    main()
    out = capsys.readouterr().out
    assert f"PyExtrusion {pyextrusion.__version__}" in out
    assert "Enrique Calvo Ordonez" in out
    assert "Apache-2.0" in out
    assert "https://pyextrusion.com" in out



def test_structured_result_blocks_match_legacy_fields():
    r = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000, front_scrap_m=2,
    )
    assert r.geometry.extrusion_ratio == pytest.approx(r.extrusion_ratio)
    assert r.billet.length_mm == pytest.approx(r.billet_length_mm)
    assert r.production.bars_per_billet == r.bars_per_billet
    assert r.scrap.fixed_kg == pytest.approx(r.fixed_scrap_kg)
    assert r.scrap.total_kg == pytest.approx(r.global_scrap_kg)
    assert r.productivity.real_net_kg_h == pytest.approx(r.real_net_kg_h)
    assert r.timing.total_min == pytest.approx(r.total_time_min)


def test_scrap_breakdown_reconciles_totals():
    r = calculate_simple(
        press(), linear_weight_kg_m=1.1, exits=3, profile_type="hollow",
        exit_speed_m_min=22, cut_length_mm=6000, bars_requested=800, front_scrap_m=2,
    )
    s = r.scrap
    fixed_sum = s.butt_kg + s.front_scrap_kg + s.billet_saw_kg + s.puller_saw_kg + s.final_saw_kg
    total_sum = fixed_sum + s.start_kg + s.complexity_kg
    assert s.fixed_kg == pytest.approx(fixed_sum)
    assert s.total_kg == pytest.approx(total_sum)


def test_butt_trace_distinguishes_rule_and_user_override():
    auto = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=100, front_scrap_m=2,
    )
    manual = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=100, front_scrap_m=2, butt_mm=20,
    )
    assert auto.billet.butt_source == "user_override"
    assert auto.process.butt_source == "user_override"
    assert manual.billet.butt_source == "user_override"
    assert manual.process.butt_source == "user_override"
    assert manual.billet.butt_mm == 20


def test_front_scrap_trace_for_multi_billet_override():
    r = calculate_simple(
        press(), linear_weight_kg_m=4.0, exits=1, profile_type="solid",
        exit_speed_m_min=15, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2, multi_billet_front_scrap_m=1,
    )
    assert r.process.standard_front_scrap_m == 2
    assert r.process.multi_billet_front_scrap_m == 1
    assert r.process.multi_billet_front_scrap_source == "user_override"
    if r.recommended_configuration == "k_billets_1_profile":
        assert r.process.applied_front_scrap_m == 1
        assert r.process.applied_front_scrap_source == "multi_billet_user_override"
    multi = next(c for c in r.configurations if c.name == "k_billets_1_profile")
    assert multi.front_scrap_source == "user_override"


def test_result_value_select_section_and_item_access():
    r = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000, front_scrap_m=2,
    )
    assert r.value("scrap.total_kg") == pytest.approx(r.global_scrap_kg)
    assert r["productivity.real_net_kg_h"] == pytest.approx(r.real_net_kg_h)
    selected = r.select("scrap.total_kg", "productivity.real_net_kg_h", "billet.length_mm")
    assert tuple(selected) == ("scrap.total_kg", "productivity.real_net_kg_h", "billet.length_mm")
    assert selected["billet.length_mm"] == pytest.approx(r.billet_length_mm)
    assert r.section("scrap")["total_kg"] == pytest.approx(r.global_scrap_kg)
    assert "scrap.total_kg" in r.field_paths()


def test_result_unknown_field_is_clear_error():
    r = calculate_simple(
        press(), linear_weight_kg_m=1.35, exits=2, profile_type="solid",
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=100, front_scrap_m=2,
    )
    with pytest.raises(KeyError, match="Unknown result field"):
        r.value("scrap.does_not_exist")


def test_cli_field_fields_and_section(monkeypatch, capsys, tmp_path):
    from pyextrusion import ProductionSpec, StudyCase, save_case_json, save_press_json
    from pyextrusion.cli import main
    press_path = tmp_path / "press.json"
    case_path = tmp_path / "case.json"
    save_press_json(press(), press_path)
    save_case_json(
        StudyCase(ProfileSpec(1.35, 2, "solid"), ProductionSpec(24, 7000, 100, front_scrap_m=2)),
        case_path,
    )
    monkeypatch.setattr("sys.argv", [
        "pyextrusion", "calculate", str(case_path), "--press", str(press_path),
        "--field", "productivity.real_net_kg_h",
    ])
    main()
    single = capsys.readouterr().out.strip()
    assert float(single) > 0

    monkeypatch.setattr("sys.argv", [
        "pyextrusion", "calculate", str(case_path), "--press", str(press_path),
        "--fields", "scrap.total_kg", "billet.length_mm", "--format", "json",
    ])
    main()
    selected = json.loads(capsys.readouterr().out)
    assert set(selected) == {"scrap.total_kg", "billet.length_mm"}

    monkeypatch.setattr("sys.argv", [
        "pyextrusion", "calculate", str(case_path), "--press", str(press_path),
        "--section", "scrap", "--format", "json",
    ])
    main()
    section = json.loads(capsys.readouterr().out)
    assert "total_kg" in section and "butt_kg" in section


def test_industrial_warning_thresholds_are_exposed():
    r = calculate_simple(
        press(), linear_weight_kg_m=1.1, exits=3, profile_type="hollow",
        exit_speed_m_min=22, cut_length_mm=6000, bars_requested=800, front_scrap_m=2,
    )
    assert any("Cuts ratio is" in w and "geometric penalty" in w for w in r.warnings)
    assert any("Fixed scrap exceeds 12%" in w for w in r.warnings)



def _v080_study():
    return StudyInput(
        press=press(), profile=ProfileSpec(1.35, 2, "solid"),
        exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000,
        front_scrap_m=2, complexity="normal",
    )

def test_v080_case_adjustment_helpers_preserve_original():
    from pyextrusion import StudyCase, Profile, Production
    case = StudyCase(
        profile=Profile(linear_weight_kg_m=1.1, exits=3, profile_type="hollow"),
        production=Production(exit_speed_m_min=22, cut_length_mm=6000, bars_requested=800, front_scrap_m=2),
    )
    adjusted = case.with_production(butt_mm=20, front_scrap_m=1.5)
    adjusted2 = adjusted.with_profile(linear_weight_kg_m=1.2)
    adjusted3 = case.replace(butt_mm=20, exits=4, exit_speed_m_min=21)
    assert case.production.butt_mm is None
    assert case.production.front_scrap_m == 2
    assert adjusted.production.butt_mm == 20
    assert adjusted.production.front_scrap_m == 1.5
    assert adjusted2.profile.linear_weight_kg_m == 1.2
    assert adjusted3.profile.exits == 4
    assert adjusted3.production.butt_mm == 20
    assert adjusted3.production.exit_speed_m_min == 21


def test_v080_unknown_case_adjustment_has_px1010():
    from pyextrusion import StudyCase, Profile, Production, InvalidStudyAdjustmentError
    case = StudyCase(Profile(1.1, profile_type="solid"), Production(20, 6000, 10))
    with pytest.raises(InvalidStudyAdjustmentError) as exc:
        case.replace(foo=123)
    assert exc.value.code == "PX1010"


def test_v080_field_glossary_is_complete_and_describable():
    from pyextrusion import list_fields, describe_field, FIELD_GLOSSARY
    fields = list_fields()
    assert len(fields) == 98
    assert len(FIELD_GLOSSARY) == 98
    info = describe_field("scrap.total_kg")
    assert info.unit == "kg"
    assert "Total losses" in info.description


def test_v080_result_field_paths_match_glossary():
    from pyextrusion import list_fields
    r = calculate(_v080_study())
    assert r.field_paths() == tuple(item.path for item in list_fields())


def test_v080_unknown_result_field_preserves_keyerror_and_px1004():
    from pyextrusion import UnknownResultFieldError, PyExtrusionError
    r = calculate(_v080_study())
    with pytest.raises(UnknownResultFieldError) as exc:
        r.value("scrap.foo")
    assert isinstance(exc.value, KeyError)
    assert isinstance(exc.value, PyExtrusionError)
    assert exc.value.code == "PX1004"


def test_v080_unknown_section_and_empty_selection_codes():
    from pyextrusion import UnknownResultSectionError, InvalidResultSelectionError
    r = calculate(_v080_study())
    with pytest.raises(UnknownResultSectionError) as exc1:
        r.section("foo")
    assert exc1.value.code == "PX1008"
    with pytest.raises(InvalidResultSelectionError) as exc2:
        r.select()
    assert exc2.value.code == "PX1009"


def test_v080_error_catalog():
    from pyextrusion import list_error_info, get_error_info
    items = list_error_info()
    assert [x.code for x in items] == [f"PX10{i:02d}" for i in range(1, 14)]
    assert get_error_info("px1004").name == "UnknownResultField"
    assert get_error_info("PX1004").cli_exit_code == 2


def test_v080_unsupported_schema_error_code():
    from pyextrusion import UnsupportedSchemaVersionError
    with pytest.raises(UnsupportedSchemaVersionError) as exc:
        study_from_dict({"schema_version": "9.9"})
    assert exc.value.code == "PX1005"


def test_v080_cli_fields_field_errors_error(monkeypatch, capsys):
    import pyextrusion.cli as cli
    monkeypatch.setattr(sys, "argv", ["pyextrusion", "field", "scrap.total_kg"])
    cli.main()
    out = capsys.readouterr().out
    assert "scrap.total_kg" in out and "kg" in out

    monkeypatch.setattr(sys, "argv", ["pyextrusion", "errors"])
    cli.main()
    out = capsys.readouterr().out
    assert "PX1004 UnknownResultField" in out

    monkeypatch.setattr(sys, "argv", ["pyextrusion", "error", "PX1010"])
    cli.main()
    out = capsys.readouterr().out
    assert "InvalidStudyAdjustment" in out


def test_v080_cli_unknown_result_field_returns_documented_code(monkeypatch, capsys, tmp_path):
    import pyextrusion.cli as cli
    from pyextrusion import save_press_json, save_case_json
    study = _v080_study()
    press_path = tmp_path / "press.json"
    case_path = tmp_path / "case.json"
    save_press_json(study.press, press_path)
    save_case_json(study.to_case(), case_path)
    monkeypatch.setattr(sys, "argv", [
        "pyextrusion", "calculate", str(case_path), "--press", str(press_path),
        "--field", "scrap.foo",
    ])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "PX1004" in err


def test_v090_profile_type_is_required_with_px1002():
    from pyextrusion import Profile, InvalidProfileInputError
    with pytest.raises(InvalidProfileInputError, match="profile.profile_type is required") as exc:
        Profile(1.0)
    assert exc.value.code == "PX1002"
    assert "solid, plate, hollow, tubular" in str(exc.value)


def test_v090_profile_type_aliases_normalize_to_canonical_values():
    from pyextrusion import Profile
    assert Profile(1.0, profile_type="solid").profile_type == "solid"
    assert Profile(1.0, profile_type="plate").profile_type == "solid"
    assert Profile(1.0, profile_type="hollow").profile_type == "hollow"
    assert Profile(1.0, profile_type="tubular").profile_type == "hollow"
    assert Profile(1.0, profile_type=" TUBULAR ").profile_type == "hollow"


def test_v090_invalid_profile_type_has_valid_values_in_error():
    from pyextrusion import Profile, InvalidProfileInputError
    with pytest.raises(InvalidProfileInputError) as exc:
        Profile(1.0, profile_type="banana")
    assert exc.value.code == "PX1002"
    assert "Valid values: solid, plate, hollow, tubular" in str(exc.value)


def test_v090_json_missing_profile_type_fails_with_px1002():
    from pyextrusion import case_from_dict, InvalidProfileInputError
    d = {
        "schema_version": "0.6",
        "profile": {"linear_weight_kg_m": 1.0, "exits": 1},
        "production": {"exit_speed_m_min": 20, "cut_length_mm": 6000, "bars_requested": 10},
    }
    with pytest.raises(InvalidProfileInputError) as exc:
        case_from_dict(d)
    assert exc.value.code == "PX1002"


def test_v090_butt_rules_accept_public_profile_aliases():
    assert ButtRule("plate", None, 20).profile_type == "solid"
    assert ButtRule("tubular", None, 25).profile_type == "hollow"


def test_v090_double_profile_losses_use_two_pulls_but_one_butt_and_billet_saw():
    p = press()
    r = calculate_simple(
        p, linear_weight_kg_m=0.4, exits=1, profile_type="plate",
        exit_speed_m_min=20, cut_length_mm=7000, bars_requested=100,
        front_scrap_m=2, butt_mm=20,
    )
    assert r.recommended_configuration == "1_billet_2_profiles"
    assert r.production.profiles_per_billet == 2
    # 8 billets × 2 pulls × 2 m × 0.4 kg/m
    assert r.scrap.front_scrap_kg == pytest.approx(12.8)
    # Butt and billet saw happen once per billet.
    assert r.scrap.butt_kg == pytest.approx(r.billets * 20 * p.billet_weight_kg_per_mm)
    assert r.scrap.billet_saw_kg == pytest.approx(r.billets * p.saws.billet_mm * p.billet_weight_kg_per_mm)
    # Puller saw happens once per pull/profile.
    assert r.scrap.puller_saw_kg == pytest.approx((p.saws.puller_mm / 1000) * 0.4 * r.billets * 2)
    physical_per_profile = (
        r.cuts * 7.0 + 2.0
        + p.saws.puller_mm / 1000.0
        + (r.cuts + 1) * p.saws.final_mm / 1000.0
    )
    assert r.timing.extrusion_per_billet_min == pytest.approx(
        2 * physical_per_profile / 20
    )


def test_v090_50000kg_case_uses_corrected_double_profile_billet_count():
    from pyextrusion import AnnualDemandSpec, Production, Profile, StudyCase, calculate_annual_demand
    case = StudyCase(
        Profile(0.8, exits=1, profile_type="plate"),
        Production(22, 7000, 1, front_scrap_m=2.5, butt_mm=20),
    )
    annual = calculate_annual_demand(press(), case, AnnualDemandSpec("kg", 50000))
    calc = annual.calculation
    assert calc.recommended_configuration == "1_billet_2_profiles"
    assert annual.normalized.bars_target == 8929
    assert calc.production.profiles_per_billet == 2
    assert calc.bars_per_billet == 14
    assert calc.billets == 638


def test_v090_field_glossary_documents_profiles_per_billet():
    from pyextrusion import describe_field
    info = describe_field("production.profiles_per_billet")
    assert info.unit == "profiles/billet"
    assert "maximum supported value is 2" in info.description


def p9_54():
    return PressSpec(
        name="Test 9in", nominal_force_t=3500, container_diameter_mm=236, billet_diameter_mm=228,
        billet_min_mm=500, billet_max_mm=1300, table_length_m=54, dead_time_sec=14,
        saws=SawSpec(5,5,4),
        butt_rules=(
            ButtRule("solid", 2.5, 15), ButtRule("solid", None, 30, min_total_linear_weight_kg_m=2.5),
            ButtRule("hollow", 2.5, 20), ButtRule("hollow", 3.5, 25, min_total_linear_weight_kg_m=2.5),
            ButtRule("hollow", None, 30, min_total_linear_weight_kg_m=3.5),
        ),
    )

def test_v010_re_status_thresholds_and_alias_behavior():
    from pyextrusion import calculate_simple, extrusion_ratio_status
    assert extrusion_ratio_status("solid", 24.99) == "low"
    assert extrusion_ratio_status("solid", 25) == "ok"
    assert extrusion_ratio_status("solid", 85) == "ok"
    assert extrusion_ratio_status("solid", 85.01) == "high"
    assert extrusion_ratio_status("hollow", 14.99) == "low"
    assert extrusion_ratio_status("hollow", 15) == "ok"
    assert extrusion_ratio_status("hollow", 75) == "ok"
    assert extrusion_ratio_status("hollow", 75.01) == "high"
    plate = calculate_simple(p9_54(), linear_weight_kg_m=1.1, exits=1, profile_type="plate", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=100, front_scrap_m=2, butt_mm=20)
    tubular = calculate_simple(p9_54(), linear_weight_kg_m=1.1, exits=1, profile_type="tubular", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=100, front_scrap_m=2, butt_mm=20)
    assert plate.geometry.extrusion_ratio_status == "high"
    assert tubular.geometry.extrusion_ratio_status == "high"
    assert plate.extrusion_ratio == pytest.approx(tubular.extrusion_ratio)

def test_v010_re_same_numeric_value_can_classify_differently():
    from pyextrusion import calculate_simple
    plate = calculate_simple(p9_54(), linear_weight_kg_m=1.477, exits=1, profile_type="plate", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=100, front_scrap_m=2, butt_mm=20)
    tubular = calculate_simple(p9_54(), linear_weight_kg_m=1.477, exits=1, profile_type="tubular", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=100, front_scrap_m=2, butt_mm=20)
    assert plate.extrusion_ratio == pytest.approx(tubular.extrusion_ratio)
    assert 75 < plate.extrusion_ratio < 85
    assert plate.extrusion_ratio_status == "ok"
    assert tubular.extrusion_ratio_status == "high"

def test_v010_direct_bar_supplement_is_explicit_and_extra_pct_uses_effective_target():
    from pyextrusion import calculate_simple
    r = calculate_simple(p9_54(), linear_weight_kg_m=1.1, exits=1, profile_type="plate", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=1000, front_scrap_m=2, butt_mm=20, supplement_10_pct=True)
    assert r.production.bars_requested == 1000
    assert r.production.bars_target_effective == 1100
    assert r.production.supplement_10_pct is True
    assert r.production.supplement_factor == pytest.approx(1.10)
    assert r.extra_bars == r.bars_manufactured - 1100
    assert r.extra_pct == pytest.approx(r.extra_bars / 1100 * 100)
    assert not any("below 10%" in w for w in r.warnings)

def test_v010_supplement_defaults_off_and_summary_is_silent_when_off():
    from pyextrusion import calculate_simple, format_result
    off = calculate_simple(p9_54(), linear_weight_kg_m=1.1, exits=1, profile_type="plate", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=1000, front_scrap_m=2, butt_mm=20)
    on = calculate_simple(p9_54(), linear_weight_kg_m=1.1, exits=1, profile_type="plate", exit_speed_m_min=30, cut_length_mm=6500, bars_requested=1000, front_scrap_m=2, butt_mm=20, supplement_10_pct=True)
    assert off.supplement_10_pct is False
    assert "Demand supplement" not in format_result(off)
    assert "Demand supplement:       10% included" in format_result(on)

def test_v010_annual_supplement_applies_before_normalization():
    from pyextrusion import AnnualDemandSpec, Production, Profile, StudyCase, calculate_annual_demand
    base_case = StudyCase(Profile(1.1, exits=1, profile_type="plate"), Production(30, 6500, 1, front_scrap_m=2, butt_mm=20))
    supp_case = base_case.with_production(supplement_10_pct=True)
    base = calculate_annual_demand(p9_54(), base_case, AnnualDemandSpec("kg", 10000))
    supp = calculate_annual_demand(p9_54(), supp_case, AnnualDemandSpec("kg", 10000))
    assert base.normalized.adjusted_source_value == pytest.approx(10000)
    assert base.normalized.bars_target == 1399
    assert supp.normalized.adjusted_source_value == pytest.approx(11000)
    assert supp.normalized.bars_target == 1539
    assert supp.calculation.production.bars_target_effective == 1539
    assert supp.calculation.production.supplement_10_pct is True
    assert supp.calculation.extra_pct == pytest.approx(supp.calculation.extra_bars / 1539 * 100)

def test_v010_extra_pct_glossary_explains_effective_target_and_not_supplement():
    from pyextrusion import describe_field
    info = describe_field("production.extra_pct")
    assert "complete-billet rounding" in info.description
    assert "independent" in info.description

def test_v010_schema_07_round_trip_persists_supplement(tmp_path):
    from pyextrusion import Production, Profile, StudyCase, save_case_json, load_case_json
    case = StudyCase(Profile(1.1, exits=1, profile_type="plate"), Production(30, 6500, 100, supplement_10_pct=True))
    path=tmp_path/"case.json"
    save_case_json(case,path)
    raw=json.loads(path.read_text())
    assert raw["schema_version"] == "1.1"
    assert raw["production"]["supplement_10_pct"] is True
    assert load_case_json(path) == case


def test_v010_cli_supplement_override(monkeypatch, capsys, tmp_path):
    from pyextrusion import Production, Profile, StudyCase, save_case_json, save_press_json
    from pyextrusion.cli import main
    pp=tmp_path/"press.json"; cp=tmp_path/"case.json"
    save_press_json(p9_54(),pp)
    save_case_json(StudyCase(Profile(1.1,1,"plate"),Production(30,6500,1000,front_scrap_m=2,butt_mm=20)),cp)
    monkeypatch.setattr("sys.argv",["pyextrusion","calculate",str(cp),"--press",str(pp),"--supplement-10-pct","--field","production.bars_target_effective"])
    main()
    assert capsys.readouterr().out.strip()=="1100"
    monkeypatch.setattr("sys.argv",["pyextrusion","calculate",str(cp),"--press",str(pp),"--no-supplement-10-pct","--field","production.bars_target_effective"])
    main()
    assert capsys.readouterr().out.strip()=="1000"