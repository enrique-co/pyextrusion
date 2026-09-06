"""Continuous technical production sequence with PyExtrusion 0.16.0."""

from datetime import datetime

from pyextrusion import (
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    ProductionOrder,
    Profile,
    calculate_production_sequence,
    format_production_sequence,
)

press = Press(name="Example 8-inch press", nominal_size_in=8, table_length_m=54)
case = PlanningCase(
    profile=Profile(1.35, exits=2, profile_type="solid"),
    process=Process(24, 7000, front_scrap_m=2),
)

orders = [
    ProductionOrder("OF-001", case, PlanningRequest.bars(300)),
    ProductionOrder("OF-002", case, PlanningRequest.billets(20)),
    ProductionOrder("OF-003", case, PlanningRequest.kg(2500)),
]

result = calculate_production_sequence(
    press,
    orders,
    start_at=datetime(2026, 9, 7, 5, 0),
)

print(format_production_sequence(result))
