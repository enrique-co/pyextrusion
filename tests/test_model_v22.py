import json
import math
import time
from pathlib import Path

import pytest

from pyextrusion import (
    AnnualDemandSpec,
    InputFileError,
    InvalidAnnualDemandError,
    InvalidPlanningRequestError,
    InvalidPressConfigurationError,
    InvalidProfileInputError,
    InvalidProductionInputError,
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    Production,
    Profile,
    SawSpec,
    StudyCase,
    calculate_case,
    calculate_planning,
    load_case_json,
    load_press_json,
    press_from_dict,
    save_press_json,
    validate_planning_request,
)


def p8(**kwargs):
    data = dict(name="8-inch", nominal_size_in=8, table_length_m=54)
    data.update(kwargs)
    return Press(**data)


def case_exit(**kwargs):
    prod = dict(exit_speed_m_min=24, cut_length_mm=7000, bars_requested=100, front_scrap_m=2)
    prod.update(kwargs)
    return StudyCase(Profile(1.35, 2, "solid"), Production(**prod))


@pytest.mark.parametrize("size", [6, 16])
def test_v22_press_nominal_boundaries_are_valid(size):
    p = Press(name=f"{size}-inch", nominal_size_in=size, table_length_m=54)
    assert p.nominal_size_in == size


@pytest.mark.parametrize("value", [5, 17, 8.0, 8.5, True, "8"])
def test_v22_press_nominal_size_is_strict_integer_6_to_16(value):
    with pytest.raises(InvalidPressConfigurationError) as exc:
        Press(name="bad", nominal_size_in=value, table_length_m=54)
    assert exc.value.code == "PX1001"


def test_v22_legacy_schema_can_migrate_whole_float_nominal_size():
    p = press_from_dict(
        {
            "name": "legacy",
            "nominal_size_in": 8.0,
            "table_length_m": 54,
        },
        schema_version="1.0",
    )
    assert p.nominal_size_in == 8


def test_v22_current_schema_does_not_coerce_float_nominal_size():
    with pytest.raises(InvalidPressConfigurationError):
        press_from_dict(
            {"name": "current", "nominal_size_in": 8.0, "table_length_m": 54},
            schema_version="1.1",
        )


@pytest.mark.parametrize("lo,hi", [(100, 100), (100, 3000), (3000, 3000)])
def test_v22_billet_configurable_boundaries(lo, hi):
    p = Press(
        name="bounds", nominal_size_in=8, table_length_m=54,
        billet_min_length_mm=lo, billet_max_length_mm=hi,
    )
    assert p.billet_min_length_mm == lo
    assert p.billet_max_length_mm == hi


@pytest.mark.parametrize("kwargs", [
    {"billet_min_length_mm": 99, "billet_max_length_mm": 1200},
    {"billet_min_length_mm": 450, "billet_max_length_mm": 3001},
    {"billet_min_length_mm": 1200, "billet_max_length_mm": 450},
])
def test_v22_invalid_billet_limits_are_controlled(kwargs):
    with pytest.raises(InvalidPressConfigurationError) as exc:
        Press(name="bad", nominal_size_in=8, table_length_m=54, **kwargs)
    assert exc.value.code == "PX1001"


@pytest.mark.parametrize("table", [10, 100, 54.5])
def test_v22_table_range_valid(table):
    assert Press(name="table", nominal_size_in=8, table_length_m=table).table_length_m == pytest.approx(table)


@pytest.mark.parametrize("table", [9.999, 100.001, True, "54"])
def test_v22_table_range_and_type_rejected(table):
    with pytest.raises(InvalidPressConfigurationError):
        Press(name="table", nominal_size_in=8, table_length_m=table)


@pytest.mark.parametrize("dead", [5, 15, 30, 12.5])
def test_v22_dead_time_range_valid(dead):
    assert Press(name="dead", nominal_size_in=8, table_length_m=54, dead_time_sec=dead).dead_time_sec == pytest.approx(dead)


@pytest.mark.parametrize("dead", [4.999, 30.001, True, "15", math.nan, math.inf])
def test_v22_dead_time_invalid(dead):
    with pytest.raises(InvalidPressConfigurationError):
        Press(name="dead", nominal_size_in=8, table_length_m=54, dead_time_sec=dead)


@pytest.mark.parametrize("kerf", [0, 3, 5.5, 10])
def test_v22_saw_kerf_valid_values(kerf):
    saws = SawSpec(kerf, kerf, kerf)
    assert saws.billet_mm == pytest.approx(kerf)


@pytest.mark.parametrize("kerf", [0.1, 2.999, 10.001, -1, True, "5", math.nan, math.inf])
def test_v22_saw_kerf_invalid_values(kerf):
    with pytest.raises(InvalidPressConfigurationError):
        SawSpec(kerf, 5, 5)


@pytest.mark.parametrize("cut", [1000, 7000, 15000, 6500.5])
def test_v22_cut_length_range_valid(cut):
    p = Press(name="long table", nominal_size_in=8, table_length_m=20)
    r = calculate_case(p, StudyCase(Profile(1.35, 2, "solid"), Production(24, cut, 10)))
    assert r.geometry.theoretical_cuts >= 1


@pytest.mark.parametrize("cut", [999, 15001, 1, 7, 6.5, True, "7000", math.nan, math.inf])
def test_v22_cut_length_unit_and_range_errors_are_rejected(cut):
    with pytest.raises(InvalidProductionInputError) as exc:
        Production(24, cut, 100)
    assert exc.value.code == "PX1003"


def test_v22_cut_must_not_exceed_table():
    p = Press(name="10m", nominal_size_in=8, table_length_m=10)
    c = StudyCase(Profile(1, 1, "solid"), Production(20, 15000, 10))
    with pytest.raises(InvalidProductionInputError) as exc:
        calculate_case(p, c)
    assert exc.value.code == "PX1003"


@pytest.mark.parametrize("exits", [2.5, True, "2", 0, -1])
def test_v22_exits_are_strict_positive_integers(exits):
    with pytest.raises(InvalidProfileInputError) as exc:
        Profile(1.0, exits, "solid")
    assert exc.value.code == "PX1002"


@pytest.mark.parametrize("bars", [3.5, True, "100", 0, -1])
def test_v22_bars_are_strict_positive_integers(bars):
    with pytest.raises(InvalidProductionInputError) as exc:
        Production(20, 6000, bars)
    assert exc.value.code == "PX1003"


@pytest.mark.parametrize("cuts", [2.5, True, "2", 0, -1])
def test_v22_manual_cuts_are_strict_positive_integers(cuts):
    with pytest.raises(InvalidProductionInputError):
        Production(20, 6000, 100, cuts=cuts)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "1.2", True])
def test_v22_profile_weight_rejects_nonfinite_and_wrong_types(value):
    with pytest.raises(InvalidProfileInputError):
        Profile(value, 1, "solid")


@pytest.mark.parametrize("speed", [1, 24, 100, 24.5])
def test_v22_exit_speed_range_valid(speed):
    r = calculate_case(p8(), case_exit(exit_speed_m_min=speed))
    assert r.geometry.exit_speed_m_min == pytest.approx(speed)
    assert r.process.speed_input_source == "exit_speed_user_value"


@pytest.mark.parametrize("speed", [0.999, 100.001, 0, -1, True, "24", math.nan, math.inf])
def test_v22_exit_speed_invalid(speed):
    with pytest.raises(InvalidProductionInputError):
        Production(speed, 7000, 10)


def test_v22_ram_speed_can_be_the_user_input_and_round_trips_physics():
    p = p8()
    reference = calculate_case(p, case_exit(exit_speed_m_min=24))
    ram = reference.geometry.ram_speed_mm_s
    ram_case = StudyCase(
        Profile(1.35, 2, "solid"),
        Production.from_ram_speed(ram_speed_mm_s=ram, cut_length_mm=7000, bars_requested=100, front_scrap_m=2),
    )
    r = calculate_case(p, ram_case)
    assert r.geometry.exit_speed_m_min == pytest.approx(24, rel=1e-12)
    assert r.geometry.ram_speed_mm_s == pytest.approx(ram, rel=1e-12)
    assert r.process.speed_input_source == "ram_speed_user_value"
    assert r.productivity.real_net_kg_h == pytest.approx(reference.productivity.real_net_kg_h, rel=1e-12)


def test_v22_both_exit_and_ram_speed_is_an_ambiguous_input_error():
    with pytest.raises(InvalidProductionInputError) as exc:
        Production(exit_speed_m_min=20, ram_speed_mm_s=1, cut_length_mm=7000, bars_requested=10)
    assert exc.value.code == "PX1003"


def test_v22_ram_speed_that_derives_exit_outside_range_is_rejected_at_calculation():
    p = p8()
    c = StudyCase(
        Profile(1.35, 2, "solid"),
        Production.from_ram_speed(ram_speed_mm_s=100, cut_length_mm=7000, bars_requested=10),
    )
    with pytest.raises(InvalidProductionInputError) as exc:
        calculate_case(p, c)
    assert exc.value.code == "PX1003"
    assert "derived" in str(exc.value).lower() or "exit" in str(exc.value).lower()


def test_v22_ram_only_json_is_supported(tmp_path):
    data = {
        "schema_version": "1.1",
        "profile": {"linear_weight_kg_m": 1.35, "exits": 2, "profile_type": "solid"},
        "production": {"ram_speed_mm_s": 0.7, "cut_length_mm": 7000, "bars_requested": 100},
    }
    path = tmp_path / "case.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    c = load_case_json(path)
    assert c.production.exit_speed_m_min is None
    assert c.production.ram_speed_mm_s == pytest.approx(0.7)


@pytest.mark.parametrize("value", [3.5, True, "20", 0])
def test_v22_planning_billets_are_strict_integers(value):
    with pytest.raises(InvalidPlanningRequestError):
        validate_planning_request(PlanningRequest.billets(value))


@pytest.mark.parametrize("value", [3.5, True, "20", 0])
def test_v22_planning_bars_are_strict_integers(value):
    with pytest.raises(InvalidPlanningRequestError):
        validate_planning_request(PlanningRequest.bars(value))


def test_v22_planning_huge_hours_overflow_is_controlled():
    pc = PlanningCase(Profile(1.35, 2, "solid"), Process(24, 7000, front_scrap_m=2))
    with pytest.raises(InvalidPlanningRequestError) as exc:
        calculate_planning(p8(), pc, PlanningRequest.hours(1e308))
    assert exc.value.code == "PX1011"


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_v22_nonfinite_json_constants_are_px1007(tmp_path, constant):
    path = tmp_path / "bad.json"
    path.write_text(
        '{"schema_version":"1.1","profile":{"linear_weight_kg_m":1,"exits":1,"profile_type":"solid"},'
        f'"production":{{"exit_speed_m_min":{constant},"cut_length_mm":6000,"bars_requested":10}}}}',
        encoding="utf-8",
    )
    with pytest.raises(InputFileError) as exc:
        load_case_json(path)
    assert exc.value.code == "PX1007"


def test_v22_directory_used_as_json_is_px1007(tmp_path):
    with pytest.raises(InputFileError) as exc:
        load_press_json(tmp_path)
    assert exc.value.code == "PX1007"


def test_v22_numeric_strings_in_json_are_controlled_px_errors(tmp_path):
    data = {
        "schema_version": "1.1",
        "profile": {"linear_weight_kg_m": 1.35, "exits": 2, "profile_type": "solid"},
        "production": {"exit_speed_m_min": "24", "cut_length_mm": 7000, "bars_requested": 100},
    }
    path = tmp_path / "bad_type.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidProductionInputError) as exc:
        load_case_json(path)
    assert exc.value.code == "PX1003"


def test_v22_container_must_be_larger_than_billet():
    with pytest.raises(InvalidPressConfigurationError):
        Press(
            name="bad geometry", table_length_m=54,
            nominal_size_in=8, billet_diameter_mm=210, container_diameter_mm=210,
        )


def test_v22_front_scrap_must_be_less_than_table():
    p = Press(name="smallest table", nominal_size_in=8, table_length_m=10)
    c = StudyCase(Profile(1, 1, "solid"), Production(20, 6000, 10, front_scrap_m=10))
    with pytest.raises(InvalidProductionInputError) as exc:
        calculate_case(p, c)
    assert exc.value.code == "PX1003"


def test_v22_100m_table_and_1m_cut_is_bounded_and_fast():
    p = Press(name="max table", nominal_size_in=8, table_length_m=100)
    c = StudyCase(Profile(0.5, 1, "solid"), Production(20, 1000, 100))
    start = time.perf_counter()
    r = calculate_case(p, c)
    elapsed = time.perf_counter() - start
    assert r.geometry.theoretical_cuts == 100
    assert elapsed < 0.2


def test_v22_annual_bars_require_integer_and_finite_values():
    with pytest.raises(InvalidAnnualDemandError):
        AnnualDemandSpec("bars", 10.5)
    with pytest.raises(InvalidAnnualDemandError):
        AnnualDemandSpec("kg", math.inf)


def test_v22_current_write_schema_is_11(tmp_path):
    path = tmp_path / "press.json"
    save_press_json(p8(), path)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == "1.1"


def test_v22_save_json_to_directory_is_px1007(tmp_path):
    with pytest.raises(InputFileError) as exc:
        save_press_json(p8(), tmp_path)
    assert exc.value.code == "PX1007"


def test_v22_cli_annual_bars_accepts_whole_integer_text(monkeypatch, capsys, tmp_path):
    from pyextrusion import save_case_json
    from pyextrusion.cli import main
    press_path = tmp_path / "press.json"
    case_path = tmp_path / "case.json"
    save_press_json(p8(), press_path)
    save_case_json(case_exit(), case_path)
    monkeypatch.setattr("sys.argv", [
        "pyextrusion", "annual", str(case_path), "--press", str(press_path),
        "--value", "300", "--unit", "bars", "--format", "json",
    ])
    main()
    data = json.loads(capsys.readouterr().out)
    assert data["normalized"]["bars_target"] == 300


def test_v22_cli_annual_bars_rejects_fraction(monkeypatch, capsys, tmp_path):
    from pyextrusion import save_case_json
    from pyextrusion.cli import main
    press_path = tmp_path / "press.json"
    case_path = tmp_path / "case.json"
    save_press_json(p8(), press_path)
    save_case_json(case_exit(), case_path)
    monkeypatch.setattr("sys.argv", [
        "pyextrusion", "annual", str(case_path), "--press", str(press_path),
        "--value", "300.5", "--unit", "bars",
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert "PX1006" in capsys.readouterr().err


def test_v22_extreme_finite_target_cannot_leak_infinity():
    p = Press(name="tiny target", nominal_size_in=8, table_length_m=54, target_net_productivity_kg_h=1e-308)
    with pytest.raises(InvalidProductionInputError) as exc:
        calculate_case(p, case_exit())
    assert exc.value.code == "PX1003"


def test_v22_extreme_profile_geometry_is_controlled_not_raw_valueerror():
    p = Press(name="tiny density", nominal_size_in=8, table_length_m=54, density_kg_m3=1e-308)
    with pytest.raises((InvalidProfileInputError, InvalidProductionInputError)) as exc:
        calculate_case(p, StudyCase(Profile(1.0, 1, "solid"), Production(20, 6000, 10)))
    assert exc.value.code in {"PX1002", "PX1003"}


def test_v22_extreme_press_geometry_is_rejected_at_configuration_boundary():
    with pytest.raises(InvalidPressConfigurationError) as exc:
        Press(
            name="overflow geometry", table_length_m=54, nominal_size_in=8,
            billet_diameter_mm=1e308, container_diameter_mm=1.01e308,
        )
    assert exc.value.code == "PX1001"
