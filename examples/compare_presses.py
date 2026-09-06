from pathlib import Path

from pyextrusion import compare_presses, format_comparison, load_case_json, load_press_json

HERE = Path(__file__).resolve().parent
case = load_case_json(HERE / "case_basic.json")
presses = [
    load_press_json(HERE / "press_example_8in.json"),
    load_press_json(HERE / "press_example_9in.json"),
]
comparison = compare_presses(presses, case)
print(format_comparison(comparison))
