"""Quantity-free process evaluation and operational planning with PyExtrusion 0.16.0."""
from pyextrusion import (
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    Profile,
    calculate_planning,
    calculate_process,
)

press = Press(name="Example 8-inch press", nominal_size_in=8, table_length_m=54)
case = PlanningCase(
    profile=Profile(1.35, 2, "solid"),
    process=Process(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        front_scrap_m=2,
    ),
)

process = calculate_process(press, case)
print("Process:")
print("  config:", process.recommended_configuration)
print("  billet mm:", round(process.billet_length_mm, 2))
print("  bars/billet:", process.bars_per_billet)
print("  billets/pull:", process.billets_per_pull)

for request in (
    PlanningRequest.bars(300),
    PlanningRequest.billets(20),
    PlanningRequest.hours(2),
):
    result = calculate_planning(press, case, request)
    print(request)
    print("  billets:", result.planned_billets)
    print("  billets/pull:", result.billets_per_pull)
    print("  pulls:", result.planned_pulls)
    print("  bars:", result.planned_bars)
    print("  good kg:", round(result.planned_good_kg, 1))
    print("  scrap kg:", round(result.planned_total_scrap_kg, 1))
    print("  time min:", round(result.time_used_min, 2))
