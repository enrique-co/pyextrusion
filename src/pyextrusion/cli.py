from __future__ import annotations
import argparse
import json
import sys
from dataclasses import replace

from .api import calculate_case, compare_presses
from .comparison import compare_processes, compare_planning, compare_production_sequences
from ._meta import __author__, __description__, __license__, __title__, __url__, __version__
from .core import calculate
from .demand import AnnualDemandSpec, calculate_annual_demand
from .planning import PlanningRequest, calculate_planning
from .sequence import calculate_production_sequence
from .fields import describe_field, list_fields, RESULT_SECTIONS
from .errors import InputFileError, PyExtrusionError, get_error_info, list_error_info
from .io import (
    load_annual_demand_json,
    load_case_json,
    load_planning_case_json,
    load_press_json,
    load_study_json,
    load_production_sequence_json,
)
from .reporting import (
    format_annual_result, format_comparison, format_press, format_result,
    format_planning_result, format_production_sequence,
    format_process_comparison, format_planning_comparison,
    format_production_sequence_comparison,
)
from .validation import (
    validate_annual_demand,
    validate_annual_demand_json,
    validate_case,
    validate_case_json,
    validate_planning_case,
    validate_planning_case_json,
    validate_press,
    validate_press_json,
    validate_study,
    validate_study_json,
    validate_production_sequence_json,
)


def _print_validation(messages) -> int:
    if not messages:
        print("OK - configuration is valid")
        return 0
    has_error = False
    for item in messages:
        if item.level == "error":
            has_error = True
        prefix = f"{item.level.upper():7}"
        if item.code:
            prefix += f" {item.code}"
        print(f"{prefix} {item.field}: {item.message}")
    return 2 if has_error else 0


def _auto_validate(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON numeric constant is not allowed: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        from .validation import ValidationMessage
        return (ValidationMessage("error", "input", str(exc), "PX1007"),)
    if not isinstance(data, dict):
        from .validation import ValidationMessage
        return (ValidationMessage("error", "input", "root must be a JSON object", "PX1007"),)
    if "orders" in data and "press" in data:
        return validate_production_sequence_json(path)
    if "annual_demand" in data:
        return validate_annual_demand_json(path)
    if "press" in data and "profile" in data and "production" in data:
        return validate_study_json(path)
    if "profile" in data and "production" in data:
        return validate_case_json(path)
    if "profile" in data and "process" in data:
        return validate_planning_case_json(path)
    return validate_press_json(path)


def _has_errors(messages) -> bool:
    return any(m.level == "error" for m in messages)


def _print_selected_result(result, args) -> None:
    """Print a full result, one section, selected fields, or one scalar field."""
    try:
        if args.field:
            value = result.value(args.field)
            if args.format == "json":
                print(json.dumps(value, indent=2 if args.pretty else None, ensure_ascii=False, allow_nan=False))
            elif isinstance(value, (dict, list, tuple)):
                print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))
            else:
                print(value)
            return

        if args.fields:
            values = result.select(*args.fields)
            if args.format == "json":
                print(json.dumps(values, indent=2 if args.pretty else None, ensure_ascii=False, allow_nan=False))
            else:
                for key, value in values.items():
                    print(f"{key}: {value}")
            return

        if args.section:
            section = result.section(args.section)
            if args.format == "json":
                print(json.dumps(section, indent=2 if args.pretty else None, ensure_ascii=False, allow_nan=False))
            else:
                for key, value in section.items():
                    print(f"{key}: {value}")
            return

        if args.format == "json":
            print(result.to_json(indent=2 if args.pretty else None))
        else:
            print(format_result(result))
    except PyExtrusionError:
        raise


def _load_planning_input(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON numeric constant is not allowed: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise InputFileError(f"Cannot read planning input {path}: {exc}") from exc
    if isinstance(data, dict) and "process" in data:
        return load_planning_case_json(path), validate_planning_case
    return load_case_json(path), validate_case


def main() -> None:
    parser = argparse.ArgumentParser(prog="pyextrusion", description=__description__)
    parser.add_argument("--version", action="version", version=f"{__title__} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    calc = sub.add_parser("calculate", help="Calculate a study or a reusable case")
    calc.add_argument("input", help="Path to study/case JSON")
    calc.add_argument("--press", help="External press JSON; makes INPUT a reusable case")
    calc.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    calc.add_argument("--pretty", action="store_true", help="Pretty-print JSON output (compatibility option)")
    selector = calc.add_mutually_exclusive_group()
    selector.add_argument("--field", help="Return one result field, e.g. scrap.total_kg")
    selector.add_argument("--fields", nargs="+", help="Return selected result fields")
    selector.add_argument(
        "--section",
        choices=["status", "geometry", "billet", "production", "scrap", "productivity", "timing", "process"],
        help="Return one structured result section",
    )
    calc.add_argument(
        "--supplement-10-pct", action=argparse.BooleanOptionalAction, default=None,
        help="Override the case and include/exclude the explicit 10%% demand supplement",
    )

    annual = sub.add_parser("annual", help="Calculate an annual demand on one press")
    annual.add_argument("case", help="Path to reusable case JSON")
    annual.add_argument("--press", required=True, help="Press JSON")
    demand_group = annual.add_mutually_exclusive_group(required=True)
    demand_group.add_argument("--demand", help="Annual demand JSON")
    demand_group.add_argument("--value", help="Annual demand value (use with --unit)")
    annual.add_argument("--unit", choices=["kg", "m", "bars"], help="Unit for --value")
    annual.add_argument("--format", choices=["json", "text"], default="text")
    annual.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    annual.add_argument(
        "--supplement-10-pct", action=argparse.BooleanOptionalAction, default=None,
        help="Override the case and include/exclude the explicit 10%% demand supplement",
    )


    plan = sub.add_parser("plan", help="Calculate an operational production plan")
    plan.add_argument("case", help="Path to PlanningCase JSON (preferred) or legacy reusable StudyCase JSON")
    plan.add_argument("--press", required=True, help="Press JSON")
    plan_group = plan.add_mutually_exclusive_group(required=True)
    plan_group.add_argument("--bars", type=int, help="Target number of finished bars")
    plan_group.add_argument("--kg", type=float, help="Minimum good-product target in kg")
    plan_group.add_argument("--metres", "--meters", dest="metres", type=float, help="Minimum good-product target in metres")
    plan_group.add_argument("--billets", type=int, help="Exact number of complete billets to extrude")
    plan_group.add_argument("--minutes", type=float, help="Available press time in minutes")
    plan_group.add_argument("--hours", type=float, help="Available press time in hours")
    plan.add_argument("--format", choices=["json", "text"], default="text")
    plan.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    sequence = sub.add_parser("sequence", help="Calculate a user-supplied production-order sequence")
    sequence.add_argument("input", help="Path to production-sequence JSON")
    sequence.add_argument("--format", choices=["json", "text"], default="text")
    sequence.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    compare_process = sub.add_parser("compare-process", help="Compare one quantity-free process on several presses")
    compare_process.add_argument("case", help="Path to PlanningCase JSON (profile + process)")
    compare_process.add_argument("presses", nargs="+", help="Two or more press JSON files")
    compare_process.add_argument("--format", choices=["json", "text"], default="text")
    compare_process.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    compare_plan = sub.add_parser("compare-planning", help="Compare one operational planning request on several presses")
    compare_plan.add_argument("case", help="Path to PlanningCase JSON (profile + process)")
    compare_plan.add_argument("presses", nargs="+", help="Two or more press JSON files")
    compare_plan_group = compare_plan.add_mutually_exclusive_group(required=True)
    compare_plan_group.add_argument("--bars", type=int)
    compare_plan_group.add_argument("--kg", type=float)
    compare_plan_group.add_argument("--metres", "--meters", dest="metres", type=float)
    compare_plan_group.add_argument("--billets", type=int)
    compare_plan_group.add_argument("--minutes", type=float)
    compare_plan_group.add_argument("--hours", type=float)
    compare_plan.add_argument("--format", choices=["json", "text"], default="text")
    compare_plan.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    compare_seq = sub.add_parser("compare-sequence", help="Compare the same production-order sequence on several presses")
    compare_seq.add_argument("input", help="Path to production-sequence JSON; its embedded press is ignored for comparison")
    compare_seq.add_argument("presses", nargs="+", help="Two or more press JSON files")
    compare_seq.add_argument("--format", choices=["json", "text"], default="text")
    compare_seq.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    comp = sub.add_parser("compare", help="Run one reusable case on several presses")
    comp.add_argument("case", help="Path to case JSON (profile + production, no press required)")
    comp.add_argument("presses", nargs="+", help="Two or more press JSON files")
    comp.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    comp.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    comp.add_argument(
        "--supplement-10-pct", action=argparse.BooleanOptionalAction, default=None,
        help="Override the case and include/exclude the explicit 10%% demand supplement",
    )

    val = sub.add_parser("validate", help="Validate press, case, demand or embedded study JSON")
    val.add_argument("input", help="Path to JSON")
    val.add_argument("--kind", choices=["auto", "press", "case", "planning", "study", "demand", "sequence"], default="auto")

    info = sub.add_parser("info", help="Show project identity, version, license and website")

    fields_cmd = sub.add_parser("fields", help="List documented public result fields")
    fields_cmd.add_argument("--section", choices=RESULT_SECTIONS, help="Limit fields to one result section")
    fields_cmd.add_argument("--format", choices=["text", "json"], default="text")

    field_cmd = sub.add_parser("field", help="Describe one documented result field")
    field_cmd.add_argument("path", help="Exact result field path, e.g. scrap.total_kg")
    field_cmd.add_argument("--format", choices=["text", "json"], default="text")

    errors_cmd = sub.add_parser("errors", help="List documented PyExtrusion error codes")
    errors_cmd.add_argument("--format", choices=["text", "json"], default="text")

    error_cmd = sub.add_parser("error", help="Describe one PyExtrusion error code")
    error_cmd.add_argument("code", help="Error code, e.g. PX1004")
    error_cmd.add_argument("--format", choices=["text", "json"], default="text")

    press_cmd = sub.add_parser("press", help="Inspect a press configuration")
    press_sub = press_cmd.add_subparsers(dest="press_command", required=True)
    show = press_sub.add_parser("show", help="Show press configuration and derived billet values")
    show.add_argument("input", help="Path to press JSON")
    show.add_argument("--format", choices=["json", "text"], default="text")

    args = parser.parse_args()

    try:
        if args.command == "info":
            print(f"{__title__} {__version__}")
            print(__description__)
            print(f"Created by {__author__}")
            print(f"License: {__license__}")
            print(f"Website: {__url__}")
            return

        if args.command == "fields":
            items = list_fields(args.section)
            if args.format == "json":
                print(json.dumps([item.to_dict() for item in items], indent=2, ensure_ascii=False, allow_nan=False))
            else:
                for item in items:
                    print(f"{item.path} [{item.unit}] - {item.description}")
            return

        if args.command == "field":
            item = describe_field(args.path)
            if args.format == "json":
                print(json.dumps(item.to_dict(), indent=2, ensure_ascii=False, allow_nan=False))
            else:
                print(f"Field: {item.path}")
                print(f"Section: {item.section}")
                print(f"Unit: {item.unit}")
                print(f"Type: {item.data_type}")
                print(f"Description: {item.description}")
            return

        if args.command == "errors":
            items = list_error_info()
            if args.format == "json":
                print(json.dumps([item.__dict__ for item in items], indent=2, ensure_ascii=False, allow_nan=False))
            else:
                for item in items:
                    print(f"{item.code} {item.name} - {item.description}")
            return

        if args.command == "error":
            try:
                item = get_error_info(args.code)
            except KeyError:
                print(f"ERROR: Unknown PyExtrusion error code: {args.code}", file=sys.stderr)
                raise SystemExit(2)
            if args.format == "json":
                print(json.dumps(item.__dict__, indent=2, ensure_ascii=False, allow_nan=False))
            else:
                print(f"Code: {item.code}")
                print(f"Name: {item.name}")
                print(f"Category: {item.category}")
                print(f"Description: {item.description}")
                print(f"Resolution: {item.resolution}")
                print(f"CLI exit code: {item.cli_exit_code}")
            return

        if args.command == "validate":
            fn = {
                "auto": _auto_validate,
                "press": validate_press_json,
                "case": validate_case_json,
                "planning": validate_planning_case_json,
                "study": validate_study_json,
                "demand": validate_annual_demand_json,
                "sequence": validate_production_sequence_json,
            }[args.kind]
            raise SystemExit(_print_validation(fn(args.input)))

        if args.command == "press" and args.press_command == "show":
            press = load_press_json(args.input)
            messages = validate_press(press)
            if _has_errors(messages):
                _print_validation(messages)
                raise SystemExit(2)
            if args.format == "json":
                print(json.dumps({
                    **press.to_dict(),
                    "derived_container_area_m2": press.container_area_m2,
                    "derived_billet_area_m2": press.billet_area_m2,
                    "derived_billet_weight_kg_per_mm": press.billet_weight_kg_per_mm,
                }, indent=2, ensure_ascii=False, allow_nan=False))
            else:
                print(format_press(press))
            return

        if args.command == "calculate":
            if args.press:
                press = load_press_json(args.press)
                case = load_case_json(args.input)
                if args.supplement_10_pct is not None:
                    case = case.with_production(supplement_10_pct=args.supplement_10_pct)
                messages = tuple(list(validate_press(press)) + list(validate_case(case)))
                if _has_errors(messages):
                    _print_validation(messages)
                    raise SystemExit(2)
                result = calculate_case(press, case)
            else:
                study = load_study_json(args.input)
                if args.supplement_10_pct is not None:
                    study = replace(study, supplement_10_pct=args.supplement_10_pct)
                messages = validate_study(study)
                if _has_errors(messages):
                    _print_validation(messages)
                    raise SystemExit(2)
                result = calculate(study)
            _print_selected_result(result, args)
            return

        if args.command == "annual":
            press = load_press_json(args.press)
            case = load_case_json(args.case)
            if args.supplement_10_pct is not None:
                case = case.with_production(supplement_10_pct=args.supplement_10_pct)
            if args.demand:
                demand = load_annual_demand_json(args.demand)
            else:
                if args.unit is None:
                    print("ERROR: --unit is required when using --value", file=sys.stderr)
                    raise SystemExit(2)
                try:
                    value = int(args.value) if args.unit == "bars" else float(args.value)
                except (TypeError, ValueError) as exc:
                    from .errors import InvalidAnnualDemandError
                    expected = "a whole integer" if args.unit == "bars" else "a number"
                    raise InvalidAnnualDemandError(
                        f"annual demand --value must be {expected} for unit {args.unit}"
                    ) from exc
                demand = AnnualDemandSpec(args.unit, value)
            messages = tuple(
                list(validate_press(press)) + list(validate_case(case)) + list(validate_annual_demand(demand))
            )
            if _has_errors(messages):
                _print_validation(messages)
                raise SystemExit(2)
            result = calculate_annual_demand(press, case, demand)
            if args.format == "json":
                print(result.to_json(indent=2 if args.pretty else None))
            else:
                print(format_annual_result(result))
            return


        if args.command == "plan":
            press = load_press_json(args.press)
            case, case_validator = _load_planning_input(args.case)
            messages = tuple(list(validate_press(press)) + list(case_validator(case)))
            if _has_errors(messages):
                _print_validation(messages)
                raise SystemExit(2)
            if args.bars is not None:
                request = PlanningRequest.bars(args.bars)
            elif args.kg is not None:
                request = PlanningRequest.kg(args.kg)
            elif args.metres is not None:
                request = PlanningRequest.metres(args.metres)
            elif args.billets is not None:
                request = PlanningRequest.billets(args.billets)
            elif args.minutes is not None:
                request = PlanningRequest.minutes(args.minutes)
            else:
                request = PlanningRequest.hours(args.hours)
            result = calculate_planning(press, case, request)
            if args.format == "json":
                print(result.to_json(indent=2 if args.pretty else None))
            else:
                print(format_planning_result(result))
            return

        if args.command == "sequence":
            press, orders, start_at = load_production_sequence_json(args.input)
            result = calculate_production_sequence(press, orders, start_at=start_at)
            if args.format == "json":
                print(result.to_json(indent=2 if args.pretty else None))
            else:
                print(format_production_sequence(result))
            return

        if args.command == "compare-process":
            if len(args.presses) < 2:
                from .errors import InvalidComparisonError
                raise InvalidComparisonError("comparison requires at least 2 presses")
            case = load_planning_case_json(args.case)
            case_messages = validate_planning_case(case)
            if _has_errors(case_messages):
                _print_validation(case_messages)
                raise SystemExit(2)
            presses = [load_press_json(path) for path in args.presses]
            for path, press in zip(args.presses, presses):
                messages = validate_press(press)
                if _has_errors(messages):
                    print(f"Invalid press file: {path}", file=sys.stderr)
                    _print_validation(messages)
                    raise SystemExit(2)
            comparison = compare_processes(presses, case)
            print(comparison.to_json(indent=2 if args.pretty else None) if args.format == "json" else format_process_comparison(comparison))
            return

        if args.command == "compare-planning":
            if len(args.presses) < 2:
                from .errors import InvalidComparisonError
                raise InvalidComparisonError("comparison requires at least 2 presses")
            case = load_planning_case_json(args.case)
            case_messages = validate_planning_case(case)
            if _has_errors(case_messages):
                _print_validation(case_messages)
                raise SystemExit(2)
            if args.bars is not None:
                request = PlanningRequest.bars(args.bars)
            elif args.kg is not None:
                request = PlanningRequest.kg(args.kg)
            elif args.metres is not None:
                request = PlanningRequest.metres(args.metres)
            elif args.billets is not None:
                request = PlanningRequest.billets(args.billets)
            elif args.minutes is not None:
                request = PlanningRequest.minutes(args.minutes)
            else:
                request = PlanningRequest.hours(args.hours)
            presses = [load_press_json(path) for path in args.presses]
            for path, press in zip(args.presses, presses):
                messages = validate_press(press)
                if _has_errors(messages):
                    print(f"Invalid press file: {path}", file=sys.stderr)
                    _print_validation(messages)
                    raise SystemExit(2)
            comparison = compare_planning(presses, case, request)
            print(comparison.to_json(indent=2 if args.pretty else None) if args.format == "json" else format_planning_comparison(comparison))
            return

        if args.command == "compare-sequence":
            if len(args.presses) < 2:
                from .errors import InvalidComparisonError
                raise InvalidComparisonError("comparison requires at least 2 presses")
            _embedded_press, orders, start_at = load_production_sequence_json(args.input)
            presses = [load_press_json(path) for path in args.presses]
            for path, press in zip(args.presses, presses):
                messages = validate_press(press)
                if _has_errors(messages):
                    print(f"Invalid press file: {path}", file=sys.stderr)
                    _print_validation(messages)
                    raise SystemExit(2)
            comparison = compare_production_sequences(presses, orders, start_at=start_at)
            print(comparison.to_json(indent=2 if args.pretty else None) if args.format == "json" else format_production_sequence_comparison(comparison))
            return

        if args.command == "compare":
            if len(args.presses) < 2:
                print("ERROR: compare requires at least two press JSON files", file=sys.stderr)
                raise SystemExit(2)
            case = load_case_json(args.case)
            if args.supplement_10_pct is not None:
                case = case.with_production(supplement_10_pct=args.supplement_10_pct)
            case_messages = validate_case(case)
            if _has_errors(case_messages):
                _print_validation(case_messages)
                raise SystemExit(2)
            presses = []
            for path in args.presses:
                press = load_press_json(path)
                messages = validate_press(press)
                if _has_errors(messages):
                    print(f"Invalid press file: {path}", file=sys.stderr)
                    _print_validation(messages)
                    raise SystemExit(2)
                presses.append(press)
            comparison = compare_presses(presses, case)
            if args.format == "json":
                print(comparison.to_json(indent=2 if args.pretty else None))
            else:
                print(format_comparison(comparison))
            return

    except PyExtrusionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.cli_exit_code)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
