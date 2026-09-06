import math
import json

import pytest

from pyextrusion import (
    InvalidPressConfigurationError,
    Press,
    Profile,
    Production,
    SawSpec,
    StudyCase,
    calculate_case,
    calculate_simple,
    load_press_json,
    save_press_json,
)


def nominal_press(size=8, table=54, **kwargs):
    return Press(name=f"Nominal {size}", nominal_size_in=size, table_length_m=table, **kwargs)


def test_v2_nominal_8_inference_defaults():
    p = nominal_press(8)
    assert p.press_force_t is None
    assert p.billet_diameter_mm == pytest.approx(203.2)
    assert p.container_diameter_mm == pytest.approx(203.2 * 1.035)
    assert p.billet_min_length_mm == 450
    assert p.billet_max_length_mm == 1200
    assert p.dead_time_sec == 15
    assert p.saws == SawSpec(5, 5, 5)
    assert p.target_net_productivity_kg_h == 1600
    assert p.target_productivity_source == "inferred_from_nominal_size"


def test_v2_table_length_is_required_even_with_nominal_size():
    with pytest.raises(InvalidPressConfigurationError, match="table_length_m is required") as exc:
        Press(name="No table", nominal_size_in=8)
    assert exc.value.code == "PX1001"


def test_v2_user_dimensions_and_target_override_nominal_defaults():
    p = Press(
        name="Real 9in",
        nominal_size_in=9,
        table_length_m=64,
        billet_diameter_mm=228,
        container_diameter_mm=236,
        billet_min_length_mm=480,
        billet_max_length_mm=1280,
        target_net_productivity_kg_h=2450,
        press_force_t=3500,
    )
    assert p.billet_diameter_mm == 228
    assert p.container_diameter_mm == 236
    assert p.billet_min_length_mm == 480
    assert p.billet_max_length_mm == 1280
    assert p.target_net_productivity_kg_h == 2450
    assert p.target_productivity_source == "user_value"
    assert p.press_force_t == 3500


def test_v2_nominal_class_can_be_inferred_from_real_billet_diameter():
    p = Press(
        name="Real 7in",
        table_length_m=51,
        billet_diameter_mm=170,
        container_diameter_mm=178,
    )
    assert p.nominal_size_in == 7
    assert p.nominal_size_source == "inferred_from_billet_diameter"
    assert p.billet_min_length_mm == 400
    assert p.billet_max_length_mm == 900
    assert p.target_net_productivity_kg_h == 1000


def test_v2_re_and_ram_speed_use_container_area_not_billet_area():
    p = Press(
        name="Area split",
        table_length_m=54,
        nominal_size_in=8,
        billet_diameter_mm=200,
        container_diameter_mm=220,
        billet_min_length_mm=300,
        billet_max_length_mm=1400,
    )
    r = calculate_simple(
        p,
        linear_weight_kg_m=1.5,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=24,
        cut_length_mm=6000,
        bars_requested=100,
    )
    area_profile = (1.5 / 2700) * 2
    area_container = math.pi * (0.220**2) / 4
    area_billet = math.pi * (0.200**2) / 4
    assert r.extrusion_ratio == pytest.approx(area_container / area_profile)
    assert r.ram_speed_m_min == pytest.approx(24 * area_profile / area_container)
    assert r.geometry.container_area_m2 == pytest.approx(area_container)
    assert r.geometry.billet_area_m2 == pytest.approx(area_billet)
    assert r.extrusion_ratio != pytest.approx(area_billet / area_profile)


def test_v2_default_butt_is_15_solid_and_20_hollow_and_can_be_overridden():
    p = nominal_press(8)
    solid = calculate_simple(
        p,
        linear_weight_kg_m=1.2,
        exits=1,
        profile_type="plate",
        exit_speed_m_min=20,
        cut_length_mm=6000,
        bars_requested=100,
    )
    hollow = calculate_simple(
        p,
        linear_weight_kg_m=1.2,
        exits=1,
        profile_type="tubular",
        exit_speed_m_min=20,
        cut_length_mm=6000,
        bars_requested=100,
    )
    manual = calculate_simple(
        p,
        linear_weight_kg_m=1.2,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=20,
        cut_length_mm=6000,
        bars_requested=100,
        butt_mm=27,
    )
    assert solid.butt_mm == 15
    assert solid.billet.butt_source == "default_rule"
    assert hollow.butt_mm == 20
    assert hollow.billet.butt_source == "default_rule"
    assert manual.butt_mm == 27
    assert manual.billet.butt_source == "user_override"


def test_v2_zero_kerf_means_no_scrap_for_that_operation():
    p = nominal_press(8, saws=SawSpec(billet_mm=0, puller_mm=0, final_mm=0))
    r = calculate_simple(
        p,
        linear_weight_kg_m=1.3,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=20,
        cut_length_mm=6000,
        bars_requested=100,
    )
    assert r.scrap.billet_saw_kg == 0
    assert r.scrap.puller_saw_kg == 0
    assert r.scrap.final_saw_kg == 0


def test_v2_recommended_billet_rounds_up_but_keeps_mathematical_length():
    p = nominal_press(8)
    r = calculate_simple(
        p,
        linear_weight_kg_m=1.27,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=21,
        cut_length_mm=6100,
        bars_requested=100,
        front_scrap_m=1.7,
    )
    assert r.billet.length_mm != int(r.billet.length_mm)
    assert r.billet.recommended_length_mm == math.ceil(r.billet.length_mm)
    assert r.recommended_billet_length_mm == math.ceil(r.billet_length_mm)


def test_v2_complexity_default_is_normal_three_percent():
    p = nominal_press(8)
    r = calculate_case(
        p,
        StudyCase(
            Profile(1.3, exits=2, profile_type="solid"),
            Production(20, 6000, 100),
        ),
    )
    assert r.scrap.complexity_kg == pytest.approx(0.03 * r.good_kg_manufactured)


def test_v2_startup_scrap_rule_is_preserved():
    p = nominal_press(8)
    one = calculate_simple(
        p, linear_weight_kg_m=1, exits=1, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=6000, bars_requested=100,
    )
    three = calculate_simple(
        p, linear_weight_kg_m=1, exits=3, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=6000, bars_requested=100,
    )
    assert one.scrap.start_kg == pytest.approx(5 * 1)
    assert three.scrap.start_kg == pytest.approx((5 + 5 * 3) * 3)


def test_v2_productivity_index_uses_relative_target_and_percentage_penalty():
    p = nominal_press(8)
    r = calculate_simple(
        p,
        linear_weight_kg_m=1.35,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=1000,
        front_scrap_m=2,
    )
    assert r.viable
    assert r.productivity.target_net_kg_h == 1600
    assert r.productivity.ratio == pytest.approx(r.real_net_kg_h / 1600)
    assert r.productivity.deficit_pct == pytest.approx(max(0, (1 - r.productivity.ratio) * 100))
    assert 0 <= r.productivity.productivity_index <= 100
    assert r.productivity_index == r.productivity.productivity_index
    assert r.productivity.productivity_index_rating in {
        "very_favorable", "favorable", "acceptable", "unfavorable", "highly_penalized"
    }


def test_v2_productivity_target_user_value_has_priority():
    p = nominal_press(9, target_net_productivity_kg_h=2600)
    r = calculate_simple(
        p, linear_weight_kg_m=2.0, exits=2, profile_type="solid",
        exit_speed_m_min=20, cut_length_mm=6000, bars_requested=100,
    )
    assert r.productivity.target_net_kg_h == 2600
    assert r.productivity.target_source == "user_value"
    assert r.process.target_productivity_source == "user_value"


def test_v2_out_of_supported_nominal_range_is_rejected():
    from pyextrusion import InvalidPressConfigurationError
    with pytest.raises(InvalidPressConfigurationError) as exc:
        Press(
            name="Small nonstandard",
            table_length_m=20,
            billet_diameter_mm=100,
            container_diameter_mm=104,
            billet_min_length_mm=200,
            billet_max_length_mm=700,
        )
    assert exc.value.code == "PX1001"


def test_v2_cut_longer_than_table_is_a_controlled_input_error():
    from pyextrusion import InvalidProductionInputError
    p = nominal_press(8, table=10)
    with pytest.raises(InvalidProductionInputError) as exc:
        calculate_simple(
            p,
            linear_weight_kg_m=1.0,
            exits=1,
            profile_type="solid",
            exit_speed_m_min=20,
            cut_length_mm=15000,
            bars_requested=100,
        )
    assert exc.value.code == "PX1003"


def test_v2_press_json_uses_canonical_fields_and_round_trips(tmp_path):
    p = nominal_press(8)
    path = tmp_path / "press.json"
    save_press_json(p, path)
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == "1.1"
    cfg = raw["press"]
    assert "press_force_t" in cfg
    assert "billet_min_length_mm" in cfg
    assert "billet_max_length_mm" in cfg
    assert "density_kg_m3" in cfg
    assert "nominal_force_t" not in cfg
    assert "recommended_min_linear_weight_kg_m" not in cfg
    assert load_press_json(path) == p


def test_v2_press_json_round_trip_preserves_inferred_provenance(tmp_path):
    p = nominal_press(8)
    assert p.billet_diameter_source == "inferred_from_nominal_size"
    assert p.container_diameter_source == "inferred_from_billet_diameter"
    assert p.billet_limits_source == "inferred_from_nominal_size"
    assert p.target_productivity_source == "inferred_from_nominal_size"

    path = tmp_path / "press_inferred.json"
    save_press_json(p, path)
    raw = json.loads(path.read_text())
    provenance = raw["press"]["_provenance"]
    assert provenance["billet_diameter_mm"] == "inferred_from_nominal_size"
    assert provenance["container_diameter_mm"] == "inferred_from_billet_diameter"

    loaded = load_press_json(path)
    assert loaded == p
    assert loaded.nominal_size_source == p.nominal_size_source
    assert loaded.billet_diameter_source == p.billet_diameter_source
    assert loaded.container_diameter_source == p.container_diameter_source
    assert loaded.billet_limits_source == p.billet_limits_source
    assert loaded.target_productivity_source == p.target_productivity_source


def test_v2_embedded_study_json_round_trip_preserves_press_provenance(tmp_path):
    from pyextrusion import load_study_json, save_study_json

    p = nominal_press(8)
    case = StudyCase(
        profile=Profile(linear_weight_kg_m=1.35, exits=2, profile_type="solid"),
        production=Production(exit_speed_m_min=24, cut_length_mm=7000, bars_requested=1000),
    )
    study = case.to_study_input(p)
    path = tmp_path / "study.json"
    save_study_json(study, path)

    loaded = load_study_json(path)
    assert loaded.press.billet_diameter_source == "inferred_from_nominal_size"
    assert loaded.press.container_diameter_source == "inferred_from_billet_diameter"
    assert loaded.press.billet_limits_source == "inferred_from_nominal_size"
    assert loaded.press.target_productivity_source == "inferred_from_nominal_size"


def test_v2_press_json_round_trip_preserves_user_provenance(tmp_path):
    p = Press(
        name="Explicit press",
        nominal_size_in=9,
        billet_diameter_mm=228,
        container_diameter_mm=236,
        billet_min_length_mm=500,
        billet_max_length_mm=1300,
        table_length_m=64,
        target_net_productivity_kg_h=2250,
    )
    path = tmp_path / "press_explicit.json"
    save_press_json(p, path)
    loaded = load_press_json(path)
    assert loaded.billet_diameter_source == "user_value"
    assert loaded.container_diameter_source == "user_value"
    assert loaded.billet_limits_source == "user_value"
    assert loaded.target_productivity_source == "user_value"


def test_v2_legacy_press_json_names_still_load():
    from pyextrusion import press_from_dict

    p = press_from_dict({
        "name": "Legacy",
        "nominal_force_t": 2500,
        "container_diameter_mm": 210,
        "billet_diameter_mm": 203,
        "billet_min_mm": 400,
        "billet_max_mm": 1200,
        "table_length_m": 54,
        "dead_time_sec": 15,
        "aluminium_density_kg_m3": 2700,
        "recommended_min_linear_weight_kg_m": 1.0,
    })
    assert p.press_force_t == 2500
    assert p.billet_min_length_mm == 400
    assert p.billet_max_length_mm == 1200
    assert p.density_kg_m3 == 2700
    assert p.recommended_min_linear_weight_kg_m is None


def test_v2_equal_min_max_billet_length_is_a_valid_fixed_range():
    p = Press(
        name="Fixed billet length",
        nominal_size_in=8,
        table_length_m=54,
        billet_min_length_mm=1000,
        billet_max_length_mm=1000,
    )
    # A fixed-length operating window is a valid press configuration. The
    # production case may or may not fit it, but the range itself is valid.
    from pyextrusion import validate_press
    assert not [m for m in validate_press(p) if m.level == "error"]


def test_v2_productivity_penalty_boundaries_match_manual():
    from pyextrusion.core import _productivity_penalty
    assert _productivity_penalty(5.0) == 0
    assert _productivity_penalty(5.0001) == 3
    assert _productivity_penalty(10.0) == 3
    assert _productivity_penalty(10.0001) == 7
    assert _productivity_penalty(15.0) == 7
    assert _productivity_penalty(15.0001) == 12
    assert _productivity_penalty(20.0) == 12
    assert _productivity_penalty(20.0001) == 20


def test_v2_productivity_index_rating_boundaries_match_manual():
    from pyextrusion.core import _productivity_rating
    assert _productivity_rating(39.999) == "highly_penalized"
    assert _productivity_rating(40.0) == "unfavorable"
    assert _productivity_rating(55.0) == "acceptable"
    assert _productivity_rating(70.0) == "favorable"
    assert _productivity_rating(85.0) == "very_favorable"


def test_v2_billet_area_is_always_derived_from_actual_diameter():
    from pyextrusion import validate_press
    p = Press(
        name="Legacy area override",
        nominal_size_in=8,
        table_length_m=54,
        billet_diameter_mm=200,
        billet_area_m2_override=0.5,  # historical field; deliberately impossible
    )
    expected = math.pi * (0.200 ** 2) / 4
    assert p.billet_area_m2 == pytest.approx(expected)
    warnings = validate_press(p)
    assert any(m.field == "press.billet_area_m2_override" and m.level == "warning" for m in warnings)


def test_v2_new_press_serialization_does_not_write_legacy_area_override():
    from pyextrusion import press_to_dict
    p = Press(
        name="Legacy area override",
        nominal_size_in=8,
        table_length_m=54,
        billet_area_m2_override=0.5,
    )
    assert "billet_area_m2_override" not in press_to_dict(p)["press"]


@pytest.mark.parametrize(
    "size, expected_min, expected_max, expected_target",
    [
        (6, 300, 800, 400),
        (7, 400, 900, 1000),
        (8, 450, 1200, 1600),
        (9, 500, 1300, 2200),
        (10, 550, 1400, 2800),
        (11, 600, 1500, 3400),
        (12, 600, 1500, 4000),
    ],
)
def test_v2_nominal_size_default_table_and_target_heuristic(size, expected_min, expected_max, expected_target):
    p = nominal_press(size, table=60)
    assert p.billet_diameter_mm == pytest.approx(size * 25.4)
    assert p.container_diameter_mm == pytest.approx(size * 25.4 * 1.035)
    assert p.billet_min_length_mm == expected_min
    assert p.billet_max_length_mm == expected_max
    assert p.target_net_productivity_kg_h == expected_target


def test_v2_inferred_nominal_size_uses_conventional_half_up_rounding():
    p = Press(
        name="Half-inch inference",
        table_length_m=60,
        billet_diameter_mm=8.5 * 25.4,
        container_diameter_mm=225,
    )
    assert p.nominal_size_in == 9


def test_v2_direct_calculation_validation_uses_documented_px_codes():
    from pyextrusion import InvalidProductionInputError
    with pytest.raises(InvalidProductionInputError) as exc:
        Production(0, 6000, 100)
    assert exc.value.code == "PX1003"
