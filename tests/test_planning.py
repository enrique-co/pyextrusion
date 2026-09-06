import json

import pytest

from pyextrusion import (
    InvalidPlanningRequestError,
    PlanningRequest,
    Press,
    Production,
    Profile,
    StudyCase,
    calculate_planning,
    format_planning_result,
)


def planning_fixture(*, supplement=False, linear_weight=1.35, exits=2, profile_type="solid"):
    press = Press(name="Planning 8in", nominal_size_in=8, table_length_m=54)
    case = StudyCase(
        profile=Profile(linear_weight, exits, profile_type),
        production=Production(
            exit_speed_m_min=24,
            cut_length_mm=7000,
            bars_requested=1,
            front_scrap_m=2,
            supplement_10_pct=supplement,
        ),
    )
    return press, case


def test_planning_300_bars_small_daily_batch():
    press, case = planning_fixture()
    result = calculate_planning(press, case, PlanningRequest.bars(300))
    assert result.process_viable
    assert result.request_fulfilled
    assert result.normalized_target_bars == 300
    assert result.bars_per_billet == 10
    assert result.planned_billets == 30
    assert result.planned_bars == 300
    assert result.planned_good_m == pytest.approx(2100.0)
    assert result.planned_good_kg == pytest.approx(2835.0)
    assert result.time_used_min == pytest.approx(53.5)


def test_planning_exact_20_billets():
    press, case = planning_fixture()
    result = calculate_planning(press, case, PlanningRequest.billets(20))
    assert result.process_viable
    assert result.request_fulfilled
    assert result.requested_billets == 20
    assert result.planned_billets == 20
    assert result.planned_bars == 200
    assert result.normalized_target_bars == 200
    assert result.calculation is not None
    assert result.calculation.billets == 20


def test_planning_kg_and_metres_are_normalized_to_complete_bars_and_billets():
    press, case = planning_fixture()
    kg_result = calculate_planning(press, case, PlanningRequest.kg(2500))
    m_result = calculate_planning(press, case, PlanningRequest.metres(1800))

    assert kg_result.normalized_target_bars == 265
    assert kg_result.planned_bars == 270
    assert kg_result.planned_good_kg >= 2500
    assert m_result.normalized_target_bars == 258
    assert m_result.planned_bars == 260
    assert m_result.planned_good_m >= 1800


def test_planning_two_hour_capacity_uses_complete_billets_only():
    press, case = planning_fixture()
    result = calculate_planning(press, case, PlanningRequest.hours(2))
    assert result.process_viable
    assert result.request_fulfilled
    assert result.available_time_min == 120
    assert result.planned_billets == 67
    assert result.planned_bars == 670
    assert result.time_used_min <= 120
    assert result.time_remaining_min == pytest.approx(120 - result.time_used_min)
    assert result.additional_time_for_next_billet_min > 0
    assert result.complete_billets_only

    next_result = calculate_planning(press, case, PlanningRequest.billets(68))
    assert next_result.time_used_min > 120


def test_planning_too_short_time_returns_zero_billets_but_keeps_process_reference():
    press, case = planning_fixture()
    result = calculate_planning(press, case, PlanningRequest.minutes(1))
    assert result.process_viable
    assert not result.request_fulfilled
    assert result.planned_billets == 0
    assert result.planned_bars == 0
    assert result.calculation is None
    assert result.reference.viable
    assert result.additional_time_for_next_billet_min == pytest.approx(
        result.reference.total_time_min - 1
    )


def test_planning_ignores_annual_supplement_and_warns():
    press, case = planning_fixture(supplement=True)
    result = calculate_planning(press, case, PlanningRequest.bars(300))
    assert result.normalized_target_bars == 300
    assert result.planned_bars == 300
    assert result.calculation is not None
    assert not result.calculation.supplement_10_pct
    assert any("supplement_10_pct is not applied" in w for w in result.warnings)


def test_planning_invalid_request_has_px1011():
    press, case = planning_fixture()
    with pytest.raises(InvalidPlanningRequestError) as exc:
        calculate_planning(press, case, PlanningRequest("billets", 2.5))
    assert exc.value.code == "PX1011"

    with pytest.raises(InvalidPlanningRequestError):
        calculate_planning(press, case, PlanningRequest("hours", 0))


def test_planning_json_and_text_output_are_app_friendly():
    press, case = planning_fixture()
    result = calculate_planning(press, case, PlanningRequest.billets(5))
    payload = json.loads(result.to_json())
    assert payload["planned_billets"] == 5
    assert payload["planned_bars"] == 50
    assert payload["bars_per_billet"] == 10
    text = format_planning_result(result)
    assert "Planned billets:" in text
    assert "Planned bars:" in text


def test_time_window_respects_double_profile_extra_dead_events():
    press = Press(name="Double profile", nominal_size_in=9, table_length_m=64)
    case = StudyCase(
        profile=Profile(0.6, 1, "solid"),
        production=Production(
            exit_speed_m_min=30,
            cut_length_mm=7000,
            bars_requested=1,
            front_scrap_m=2,
        ),
    )
    reference = calculate_planning(press, case, PlanningRequest.billets(1))
    assert reference.recommended_configuration == "1_billet_2_profiles"
    assert reference.calculation is not None
    assert reference.calculation.dead_time_events == 1

    available = reference.time_used_min * 3 + 0.01
    capacity = calculate_planning(press, case, PlanningRequest.minutes(available))
    assert capacity.calculation is not None
    assert capacity.time_used_min <= available
    next_plan = calculate_planning(
        press, case, PlanningRequest.billets(capacity.planned_billets + 1)
    )
    assert next_plan.time_used_min > available


def test_nonviable_process_returns_zero_operational_plan():
    press = Press(name="Heavy process", nominal_size_in=8, table_length_m=10)
    case = StudyCase(
        profile=Profile(25.0, 1, "solid"),
        production=Production(
            exit_speed_m_min=20,
            cut_length_mm=10000,
            bars_requested=1,
            front_scrap_m=0,
        ),
    )
    result = calculate_planning(press, case, PlanningRequest.billets(20))
    assert not result.process_viable
    assert not result.request_fulfilled
    assert result.planned_billets == 0
    assert result.planned_bars == 0
    assert not result.reference.viable


def test_v014_calculate_process_is_quantity_free_and_matches_order_geometry():
    from pyextrusion import PlanningCase, Process, calculate_case, calculate_process

    press = Press(name="Planning 8in", nominal_size_in=8, table_length_m=54)
    pc = PlanningCase(
        profile=Profile(1.35, 2, "solid"),
        process=Process(24, 7000, front_scrap_m=2),
    )
    process = calculate_process(press, pc)
    assert process.viable
    assert process.supported
    payload = process.to_dict()
    assert "bars_requested" not in payload
    assert "billets" not in payload
    assert process.bars_per_billet == 10
    assert process.billet_length_mm > 0

    for bars in (1, 300, 5000):
        calc = calculate_case(press, pc.to_study_case(bars))
        assert calc.recommended_configuration == process.recommended_configuration
        assert calc.cuts == process.cuts
        assert calc.bars_per_billet == process.bars_per_billet
        assert calc.billets_per_pull == process.billets_per_pull
        assert calc.billet_length_mm == pytest.approx(process.billet_length_mm)
        assert calc.table_occupancy_length_m == pytest.approx(process.table_occupancy_length_m)
        assert calc.extrusion_ratio == pytest.approx(process.extrusion_ratio)


def test_v014_short_time_window_does_not_create_a_fictitious_order(monkeypatch):
    import pyextrusion.planning as planning_module
    from pyextrusion import PlanningCase, Process

    press = Press(name="Planning 8in", nominal_size_in=8, table_length_m=54)
    pc = PlanningCase(Profile(1.35, 2, "solid"), Process(24, 7000, front_scrap_m=2))

    def forbidden(*args, **kwargs):
        raise AssertionError("calculate_case must not be called when no complete billet fits")

    monkeypatch.setattr(planning_module, "calculate_case", forbidden)
    result = planning_module.calculate_planning(press, pc, PlanningRequest.minutes(0.1))
    assert result.process.viable
    assert not result.request_fulfilled
    assert result.planned_billets == 0
    assert result.calculation is None
    assert result.additional_time_for_next_billet_min > 0


def test_v014_planning_result_exposes_process_and_operational_scrap():
    from pyextrusion import PlanningCase, Process

    press = Press(name="Planning 8in", nominal_size_in=8, table_length_m=54)
    pc = PlanningCase(Profile(1.35, 2, "solid"), Process(24, 7000, front_scrap_m=2))
    result = calculate_planning(press, pc, PlanningRequest.bars(300))
    assert result.process.bars_per_billet == result.bars_per_billet
    assert result.billet_length_mm == pytest.approx(result.process.billet_length_mm)
    assert result.table_occupancy_length_m == pytest.approx(result.process.table_occupancy_length_m)
    assert result.planned_fixed_scrap_kg > 0
    assert result.planned_total_scrap_kg >= result.planned_fixed_scrap_kg
    assert result.planned_total_scrap_pct > 0
    payload = result.to_dict()
    assert payload["process"]["bars_per_billet"] == result.bars_per_billet
    assert payload["planned_total_scrap_kg"] == pytest.approx(result.planned_total_scrap_kg)


def test_v014_legacy_studycase_is_only_a_compatibility_bridge():
    press, case = planning_fixture(supplement=True)
    result = calculate_planning(press, case, PlanningRequest.bars(300))
    assert result.normalized_target_bars == 300
    assert result.planned_bars == 300
    assert any("StudyCase planning compatibility is deprecated" in w for w in result.warnings)
    assert any("supplement_10_pct is not applied" in w for w in result.warnings)


def test_v014_extreme_minutes_are_controlled_without_hidden_order_cap():
    from pyextrusion import PlanningCase, Process, InvalidPlanningRequestError

    press = Press(name="Planning 8in", nominal_size_in=8, table_length_m=54)
    pc = PlanningCase(Profile(1.35, 2, "solid"), Process(24, 7000, front_scrap_m=2))
    with pytest.raises(InvalidPlanningRequestError):
        calculate_planning(press, pc, PlanningRequest.minutes(1e308))
