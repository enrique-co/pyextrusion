from datetime import datetime
import json

import pytest

from pyextrusion import (
    InvalidComparisonError,
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    ProductionOrder,
    Profile,
    compare_planning,
    compare_processes,
    compare_production_sequences,
    format_planning_comparison,
    format_process_comparison,
    format_production_sequence_comparison,
)


def presses():
    return (
        Press(name="Compare 8in", nominal_size_in=8, table_length_m=54),
        Press(name="Compare 9in", nominal_size_in=9, table_length_m=64),
        Press(name="Compare 10in", nominal_size_in=10, table_length_m=70),
    )


def case():
    return PlanningCase(
        Profile(1.35, 2, "solid"),
        Process(24, 7000, front_scrap_m=2),
    )


def test_compare_processes_preserves_press_order_without_winner():
    result = compare_processes(presses(), case())
    assert result.press_count == 3
    assert [r.press_name for r in result.results] == ["Compare 8in", "Compare 9in", "Compare 10in"]
    assert result.to_dict()["automatic_winner"] is None
    assert len(result.viable_results) >= 1
    payload = json.loads(result.to_json())
    assert payload["comparison_type"] == "process"
    assert payload["press_count"] == 3


def test_compare_planning_applies_exact_same_request_to_every_press():
    request = PlanningRequest.bars(300)
    result = compare_planning(presses(), case(), request)
    assert result.press_count == 3
    assert result.request == request
    assert [r.request for r in result.results] == [request, request, request]
    assert [r.press_name for r in result.results] == ["Compare 8in", "Compare 9in", "Compare 10in"]
    assert result.to_dict()["automatic_winner"] is None
    assert all(r.planned_bars >= 300 for r in result.fulfilled_results)


def test_compare_sequence_applies_same_order_list_and_same_order_on_each_press():
    c = case()
    orders = (
        ProductionOrder("OF-003", c, PlanningRequest.bars(300)),
        ProductionOrder("OF-001", c, PlanningRequest.billets(20)),
        ProductionOrder("OF-002", c, PlanningRequest.kg(2500)),
    )
    result = compare_production_sequences(presses(), orders)
    assert result.press_count == 3
    assert result.to_dict()["automatic_winner"] is None
    for sequence in result.results:
        assert [entry.order_id for entry in sequence.orders] == ["OF-003", "OF-001", "OF-002"]
        assert sequence.total_orders == 3


def test_compare_sequence_generator_is_materialized_once_for_all_presses():
    c = case()
    orders = (ProductionOrder(str(i), c, PlanningRequest.bars(10 + i)) for i in range(3))
    result = compare_production_sequences(presses(), orders)
    for sequence in result.results:
        assert [entry.order_id for entry in sequence.orders] == ["0", "1", "2"]


def test_compare_sequence_same_start_at_is_applied_to_each_press():
    c = case()
    start = datetime(2026, 9, 7, 5, 0)
    result = compare_production_sequences(
        presses(),
        [ProductionOrder("A", c, PlanningRequest.bars(300))],
        start_at=start,
    )
    assert all(sequence.start_at == start for sequence in result.results)
    assert all(sequence.theoretical_end_at is not None for sequence in result.results)


def test_comparison_requires_at_least_two_presses():
    one = presses()[:1]
    with pytest.raises(InvalidComparisonError) as exc:
        compare_processes(one, case())
    assert exc.value.code == "PX1013"
    with pytest.raises(InvalidComparisonError):
        compare_planning(one, case(), PlanningRequest.bars(10))
    with pytest.raises(InvalidComparisonError):
        compare_production_sequences(one, [ProductionOrder("A", case(), PlanningRequest.bars(10))])


def test_comparison_rejects_wrong_public_input_types():
    p = presses()
    with pytest.raises(InvalidComparisonError, match="PlanningCase"):
        compare_processes(p, "bad")
    with pytest.raises(InvalidComparisonError, match="PlanningRequest"):
        compare_planning(p, case(), "bad")
    with pytest.raises(InvalidComparisonError, match="ProductionOrder"):
        compare_production_sequences(p, ["bad"])
    with pytest.raises(InvalidComparisonError, match="datetime"):
        compare_production_sequences(
            p,
            [ProductionOrder("A", case(), PlanningRequest.bars(10))],
            start_at="2026-09-07",
        )


def test_comparison_formatters_state_no_automatic_decision():
    p = presses()
    c = case()
    process_text = format_process_comparison(compare_processes(p, c))
    planning_text = format_planning_comparison(compare_planning(p, c, PlanningRequest.bars(300)))
    sequence_text = format_production_sequence_comparison(
        compare_production_sequences(p, [ProductionOrder("A", c, PlanningRequest.bars(300))])
    )
    assert "does not rank" in process_text
    assert "does not rank" in planning_text
    assert "No allocation" in sequence_text
