from pathlib import Path

from pyextrusion import AnnualDemandSpec, calculate_annual_demand, load_case_json, load_press_json

HERE = Path(__file__).resolve().parent
press = load_press_json(HERE / "press_example_8in.json")
case = load_case_json(HERE / "case_basic.json")
result = calculate_annual_demand(press, case, AnnualDemandSpec("kg", 20_000))

print(result.to_json(indent=2))
