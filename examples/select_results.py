"""Request complete, partial, or scalar results through the public result API."""
from pathlib import Path

from pyextrusion import calculate_case, load_case_json, load_press_json

HERE = Path(__file__).resolve().parent
press = load_press_json(HERE / "press_example_8in.json")
case = load_case_json(HERE / "case_basic.json")
result = calculate_case(press, case)

print("One value:", result.value("scrap.total_kg"))
print("One section:", result.section("productivity"))
print("Selected:", result.select(
    "scrap.total_kg",
    "productivity.real_net_kg_h",
    "productivity.productivity_index",
    "billet.recommended_length_mm",
))
