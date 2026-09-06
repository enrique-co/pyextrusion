from datetime import datetime, timezone
import json

import pytest

from pyextrusion import (
    InvalidProductionSequenceError,
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    ProductionOrder,
    Profile,
    calculate_planning,
    calculate_production_sequence,
    format_production_sequence,
)


def press_fixture():
    return Press(name="Sequence 8in", nominal_size_in=8, table_length_m=54)


def case_fixture(*, weight=1.35, exits=2, speed=24, cut=7000, front=2):
    return PlanningCase(
        profile=Profile(weight, exits, "solid"),
        process=Process(speed, cut, front_scrap_m=front),
    )


def test_sequence_preserves_user_order_and_chains_without_inserted_gaps():
    press = press_fixture()
    case = case_fixture()
    orders = [
        ProductionOrder("OF-003", case, PlanningRequest.bars(300)),
        ProductionOrder("OF-001", case, PlanningRequest.billets(20)),
        ProductionOrder("OF-002", case, PlanningRequest.kg(2500)),
    ]

    result = calculate_production_sequence(press, orders)

    assert [entry.order_id for entry in result.orders] == ["OF-003", "OF-001", "OF-002"]
    assert result.total_orders == 3
    assert result.all_orders_fulfilled
    assert result.unresolved_order_ids == ()

    assert result.orders[0].cumulative_start_min == 0
    assert result.orders[0].cumulative_end_min == pytest.approx(result.orders[0].duration_min)
    assert result.orders[1].cumulative_start_min == pytest.approx(result.orders[0].cumulative_end_min)
    assert result.orders[2].cumulative_start_min == pytest.approx(result.orders[1].cumulative_end_min)
    assert result.total_press_time_min == pytest.approx(result.orders[-1].cumulative_end_min)


def test_sequence_totals_equal_sum_of_individual_planning_results():
    press = press_fixture()
    case = case_fixture()
    orders = (
        ProductionOrder("A", case, PlanningRequest.bars(300)),
        ProductionOrder("B", case, PlanningRequest.billets(20)),
        ProductionOrder("C", case, PlanningRequest.metres(1800)),
    )
    individual = [calculate_planning(press, o.case, o.request) for o in orders]
    result = calculate_production_sequence(press, orders)

    assert result.total_planned_billets == sum(p.planned_billets for p in individual)
    assert result.total_planned_pulls == sum(p.planned_pulls for p in individual)
    assert result.total_planned_bars == sum(p.planned_bars for p in individual)
    assert result.total_planned_good_m == pytest.approx(sum(p.planned_good_m for p in individual))
    assert result.total_planned_good_kg == pytest.approx(sum(p.planned_good_kg for p in individual))
    assert result.total_fixed_scrap_kg == pytest.approx(sum(p.planned_fixed_scrap_kg for p in individual))
    assert result.total_scrap_kg == pytest.approx(sum(p.planned_total_scrap_kg for p in individual))
    assert result.total_press_time_min == pytest.approx(sum(p.time_used_min for p in individual))


def test_sequence_optional_start_at_produces_theoretical_contiguous_times():
    press = press_fixture()
    case = case_fixture()
    start = datetime(2026, 9, 7, 5, 0, tzinfo=timezone.utc)
    result = calculate_production_sequence(
        press,
        [
            ProductionOrder("A", case, PlanningRequest.bars(300)),
            ProductionOrder("B", case, PlanningRequest.billets(20)),
        ],
        start_at=start,
    )

    assert result.start_at == start
    assert result.orders[0].theoretical_start_at == start
    assert result.orders[0].theoretical_end_at == result.orders[1].theoretical_start_at
    assert result.theoretical_end_at == result.orders[-1].theoretical_end_at
    assert result.theoretical_end_at > start


def test_sequence_without_start_at_does_not_invent_clock_times():
    result = calculate_production_sequence(
        press_fixture(),
        [ProductionOrder("A", case_fixture(), PlanningRequest.bars(10))],
    )
    assert result.start_at is None
    assert result.theoretical_end_at is None
    assert result.orders[0].theoretical_start_at is None
    assert result.orders[0].theoretical_end_at is None


def test_sequence_rejects_capacity_window_requests_as_orders():
    case = case_fixture()
    with pytest.raises(InvalidProductionSequenceError) as exc:
        ProductionOrder("A", case, PlanningRequest.hours(2))
    assert exc.value.code == "PX1012"
    assert "bars, kg, m or billets" in str(exc.value)

    with pytest.raises(InvalidProductionSequenceError):
        ProductionOrder("A", case, PlanningRequest.minutes(90))


def test_sequence_rejects_empty_list_and_non_order_items():
    press = press_fixture()
    with pytest.raises(InvalidProductionSequenceError, match="at least one"):
        calculate_production_sequence(press, [])
    with pytest.raises(InvalidProductionSequenceError, match="ProductionOrder"):
        calculate_production_sequence(press, ["OF-001"])


def test_sequence_requires_planning_case_and_datetime_objects():
    from pyextrusion import Production, StudyCase

    press = press_fixture()
    study = StudyCase(Profile(1.35, 2, "solid"), Production(24, 7000, 300, front_scrap_m=2))
    with pytest.raises(InvalidProductionSequenceError, match="PlanningCase"):
        ProductionOrder("A", study, PlanningRequest.bars(300))

    order = ProductionOrder("A", case_fixture(), PlanningRequest.bars(300))
    with pytest.raises(InvalidProductionSequenceError, match="datetime"):
        calculate_production_sequence(press, [order], start_at="2026-09-07T05:00:00")


def test_sequence_keeps_unresolved_order_in_position_with_zero_duration():
    press = Press(name="Short table", nominal_size_in=8, table_length_m=10)
    impossible = PlanningCase(
        Profile(25.0, 1, "solid"),
        Process(20, 10000, front_scrap_m=0),
    )
    normal = PlanningCase(
        Profile(1.35, 2, "solid"),
        Process(24, 7000, front_scrap_m=2),
    )
    result = calculate_production_sequence(
        press,
        [
            ProductionOrder("IMP", impossible, PlanningRequest.billets(20)),
            ProductionOrder("OK", normal, PlanningRequest.bars(100)),
        ],
    )

    assert [e.order_id for e in result.orders] == ["IMP", "OK"]
    assert not result.orders[0].request_fulfilled
    assert result.orders[0].duration_min == 0
    assert result.orders[1].cumulative_start_min == 0
    assert not result.all_orders_fulfilled
    assert result.unresolved_order_ids == ("IMP",)
    assert any("contribute 0 minutes" in w for w in result.warnings)


def test_sequence_result_json_is_strict_and_contains_calculated_list():
    press = press_fixture()
    result = calculate_production_sequence(
        press,
        [ProductionOrder("A", case_fixture(), PlanningRequest.bars(300))],
        start_at=datetime(2026, 9, 7, 5, 0),
    )
    payload = json.loads(result.to_json())
    assert payload["press_name"] == "Sequence 8in"
    assert payload["total_orders"] == 1
    assert payload["orders"][0]["order_id"] == "A"
    assert payload["orders"][0]["planning"]["planned_bars"] == result.orders[0].planned_bars
    assert payload["start_at"] == "2026-09-07T05:00:00"


def test_sequence_formatter_states_continuous_technical_scope():
    result = calculate_production_sequence(
        press_fixture(),
        [ProductionOrder("A", case_fixture(), PlanningRequest.bars(300))],
    )
    text = format_production_sequence(result)
    assert "production sequence" in text.lower()
    assert "A:" in text
    assert "continuous technical press times only" in text


def test_sequence_accepts_generator_and_order_ids_do_not_need_to_be_unique():
    press = press_fixture()
    case = case_fixture()
    orders = (ProductionOrder("SAME", case, PlanningRequest.bars(v)) for v in (10, 20))
    result = calculate_production_sequence(press, orders)
    assert result.total_orders == 2
    assert [e.order_id for e in result.orders] == ["SAME", "SAME"]


def test_production_order_rejects_blank_id_and_invalid_request_value():
    from pyextrusion import InvalidPlanningRequestError

    with pytest.raises(InvalidProductionSequenceError):
        ProductionOrder("   ", case_fixture(), PlanningRequest.bars(10))
    with pytest.raises(InvalidPlanningRequestError):
        ProductionOrder("A", case_fixture(), PlanningRequest.bars(2.5))


def test_sequence_input_json_roundtrip(tmp_path):
    from pyextrusion import load_production_sequence_json, save_production_sequence_json

    press = press_fixture()
    case = case_fixture()
    orders = [
        ProductionOrder("A", case, PlanningRequest.bars(300)),
        ProductionOrder("B", case, PlanningRequest.billets(20)),
    ]
    start = datetime(2026, 9, 7, 5, 0, tzinfo=timezone.utc)
    path = tmp_path / "sequence.json"
    save_production_sequence_json(press, orders, path, start_at=start)

    loaded_press, loaded_orders, loaded_start = load_production_sequence_json(path)
    assert loaded_press == press
    assert loaded_orders == tuple(orders)
    assert loaded_start == start

    result = calculate_production_sequence(loaded_press, loaded_orders, start_at=loaded_start)
    assert result.total_orders == 2
    assert result.orders[0].order_id == "A"


def test_sequence_input_json_rejects_time_window_and_bad_timestamp(tmp_path):
    from pyextrusion import load_production_sequence_json

    payload = {
        "schema_version": "1.1",
        "press": press_fixture().to_dict(),
        "start_at": "not-a-date",
        "orders": [
            {
                "order_id": "A",
                "case": {
                    "profile": case_fixture().profile.to_dict(),
                    "process": case_fixture().process.to_dict(),
                },
                "request": {"mode": "bars", "value": 300},
            }
        ],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InvalidProductionSequenceError, match="ISO-8601"):
        load_production_sequence_json(path)

    payload["start_at"] = None
    payload["orders"][0]["request"] = {"mode": "hours", "value": 2}
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InvalidProductionSequenceError, match="bars, kg, m or billets"):
        load_production_sequence_json(path)


def test_sequence_cli_json_and_auto_validation(monkeypatch, capsys, tmp_path):
    from pyextrusion import save_production_sequence_json
    from pyextrusion.cli import main

    press = press_fixture()
    orders = [ProductionOrder("A", case_fixture(), PlanningRequest.bars(300))]
    path = tmp_path / "sequence.json"
    save_production_sequence_json(press, orders, path)

    monkeypatch.setattr("sys.argv", ["pyextrusion", "validate", str(path)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "OK - configuration is valid" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["pyextrusion", "sequence", str(path), "--format", "json"])
    main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_orders"] == 1
    assert payload["orders"][0]["order_id"] == "A"
