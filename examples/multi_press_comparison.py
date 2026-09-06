"""Compare one process, one planning request and one order sequence on several presses."""

from pyextrusion import (
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

presses = [
    Press(name="Example 8-inch press", nominal_size_in=8, table_length_m=54),
    Press(name="Example 9-inch press", nominal_size_in=9, table_length_m=64),
    Press(name="Example 10-inch press", nominal_size_in=10, table_length_m=70),
]

case = PlanningCase(
    profile=Profile(1.35, exits=2, profile_type="solid"),
    process=Process(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        front_scrap_m=2,
    ),
)

process_comparison = compare_processes(presses, case)
print(format_process_comparison(process_comparison))
print()

planning_comparison = compare_planning(
    presses,
    case,
    PlanningRequest.bars(300),
)
print(format_planning_comparison(planning_comparison))
print()

orders = [
    ProductionOrder("OF-001", case, PlanningRequest.bars(300)),
    ProductionOrder("OF-002", case, PlanningRequest.billets(20)),
    ProductionOrder("OF-003", case, PlanningRequest.kg(2500)),
]
sequence_comparison = compare_production_sequences(presses, orders)
print(format_production_sequence_comparison(sequence_comparison))
