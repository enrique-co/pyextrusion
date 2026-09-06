"""Derive study variants without mutating the source case."""
from pathlib import Path

from pyextrusion import calculate_case, load_case_json, load_press_json

HERE = Path(__file__).resolve().parent
press = load_press_json(HERE / "press_example_8in.json")
case = load_case_json(HERE / "case_basic.json")

manual = case.replace(
    butt_mm=20,
    front_scrap_m=1.5,
    multi_billet_front_scrap_m=1.0,
)

base_result = calculate_case(press, case)
manual_result = calculate_case(press, manual)

print("Base butt:", base_result.billet.butt_mm, base_result.billet.butt_source)
print("Manual butt:", manual_result.billet.butt_mm, manual_result.billet.butt_source)
print("Manual scrap:", manual_result.scrap.total_kg)
