from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Iterable

from .models import (
    PressSpec,
    SawSpec,
    ButtRule,
    ProfileSpec,
    ProductionSpec,
    ProcessSpec,
    PlanningCase,
    StudyCase,
    StudyInput,
)
from .demand import AnnualDemandSpec
from .planning import PlanningRequest
from .sequence import ProductionOrder
from .errors import (
    InputFileError, UnsupportedSchemaVersionError, InvalidPressConfigurationError,
    InvalidProfileInputError, InvalidProductionInputError, InvalidAnnualDemandError,
    InvalidProductionSequenceError,
)

SUPPORTED_SCHEMA_VERSIONS = {"0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.1"}
CURRENT_SCHEMA_VERSION = "1.1"

_PRESS_PROVENANCE_KEY = "_provenance"
_PRESS_PROVENANCE_ATTRS = {
    "nominal_size_in": ("_nominal_size_source", {"user_value", "inferred_from_billet_diameter", "unavailable"}),
    "billet_diameter_mm": ("_billet_diameter_source", {"user_value", "inferred_from_nominal_size"}),
    "container_diameter_mm": ("_container_diameter_source", {"user_value", "inferred_from_billet_diameter"}),
    "billet_limits": ("_billet_limits_source", {"user_value", "inferred_from_nominal_size"}),
    "target_net_productivity_kg_h": ("_target_productivity_source", {"user_value", "inferred_from_nominal_size", "unavailable"}),
}


def _press_provenance_dict(press: PressSpec) -> dict[str, str]:
    return {
        "nominal_size_in": press.nominal_size_source,
        "billet_diameter_mm": press.billet_diameter_source,
        "container_diameter_mm": press.container_diameter_source,
        "billet_limits": press.billet_limits_source,
        "target_net_productivity_kg_h": press.target_productivity_source,
    }


def _press_dict_with_provenance(press: PressSpec) -> dict:
    data = press.to_dict()
    data[_PRESS_PROVENANCE_KEY] = _press_provenance_dict(press)
    return data


def _restore_press_provenance(press: PressSpec, provenance: Any) -> PressSpec:
    if provenance is None:
        return press
    provenance = _require_mapping(provenance, "press._provenance")
    for key, value in provenance.items():
        if key not in _PRESS_PROVENANCE_ATTRS:
            raise InvalidPressConfigurationError(f"Unknown press provenance field: {key}")
        attr, allowed = _PRESS_PROVENANCE_ATTRS[key]
        if not isinstance(value, str):
            raise InvalidPressConfigurationError(f"Invalid provenance value type for press.{key}: expected string")
        source = value
        if source not in allowed:
            raise InvalidPressConfigurationError(
                f"Invalid provenance value for press.{key}: {source!r}; allowed: {sorted(allowed)}"
            )
        object.__setattr__(press, attr, source)
    return press


def _require_mapping(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise InputFileError(f"{name} must be a JSON object")
    return value


def _reject_nonfinite_json_constant(value: str):
    raise ValueError(f"non-finite JSON numeric constant is not allowed: {value}")


def _read_json(path: str | Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f, parse_constant=_reject_nonfinite_json_constant)
    except FileNotFoundError as exc:
        raise InputFileError(f"File not found: {path}") from exc
    except (IsADirectoryError, PermissionError, UnicodeError, OSError) as exc:
        raise InputFileError(f"Cannot read input file {path}: {exc}") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise InputFileError(f"Invalid JSON in {path}: {exc}") from exc
    return _require_mapping(data, "root")


def _check_schema(d: dict) -> str:
    schema_version = str(d.get("schema_version", CURRENT_SCHEMA_VERSION))
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSchemaVersionError(
            f"Unsupported schema_version={schema_version!r}; supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    return schema_version


def press_from_dict(d: dict, *, schema_version: str | None = None) -> PressSpec:
    d = _require_mapping(d, "press")
    provenance = d.get(_PRESS_PROVENANCE_KEY)
    base_input = dict(d)
    # Compatibility migration: schemas through 1.0 historically serialized
    # nominal_size_in as 8.0/9.0 even though the value represented a whole inch.
    if schema_version is not None and schema_version != "1.1":
        nominal = base_input.get("nominal_size_in")
        if isinstance(nominal, float) and nominal.is_integer():
            base_input["nominal_size_in"] = int(nominal)
    try:
        saw_data = _require_mapping(d.get("saws", {}), "press.saws")
        saws = SawSpec(**saw_data)
        rules_raw = d.get("butt_rules", [])
        if not isinstance(rules_raw, list):
            raise InputFileError("press.butt_rules must be a JSON array")
        rules = tuple(ButtRule(**_require_mapping(r, "press.butt_rules[]")) for r in rules_raw)
        base = {k: v for k, v in base_input.items() if k not in {"saws", "butt_rules", "schema_version", _PRESS_PROVENANCE_KEY}}
        press = PressSpec(**base, saws=saws, butt_rules=rules)
    except TypeError as exc:
        raise InvalidPressConfigurationError(f"Invalid press configuration: {exc}") from exc
    return _restore_press_provenance(press, provenance)


def production_from_dict(d: dict) -> ProductionSpec:
    d = dict(_require_mapping(d, "production"))
    if "ram_speed_mm_s" in d and "exit_speed_m_min" not in d:
        d["exit_speed_m_min"] = None
    try:
        return ProductionSpec(**d)
    except TypeError as exc:
        raise InvalidProductionInputError(f"Invalid production configuration: {exc}") from exc


def process_from_dict(d: dict) -> ProcessSpec:
    d = dict(_require_mapping(d, "process"))
    if "ram_speed_mm_s" in d and "exit_speed_m_min" not in d:
        d["exit_speed_m_min"] = None
    try:
        return ProcessSpec(**d)
    except TypeError as exc:
        raise InvalidProductionInputError(f"Invalid process configuration: {exc}") from exc


def planning_case_from_dict(d: dict) -> PlanningCase:
    d = _require_mapping(d, "planning_case")
    _check_schema(d)
    profile_data = _require_mapping(d.get("profile"), "profile")
    process_data = _require_mapping(d.get("process"), "process")
    try:
        profile = ProfileSpec(**profile_data)
    except TypeError as exc:
        raise InvalidProfileInputError(f"Invalid profile configuration: {exc}") from exc
    return PlanningCase(profile=profile, process=process_from_dict(process_data))


def case_from_dict(d: dict) -> StudyCase:
    d = _require_mapping(d, "case")
    _check_schema(d)
    profile_data = _require_mapping(d.get("profile"), "profile")
    production_data = _require_mapping(d.get("production"), "production")
    try:
        profile = ProfileSpec(**profile_data)
    except TypeError as exc:
        raise InvalidProfileInputError(f"Invalid profile configuration: {exc}") from exc
    return StudyCase(profile=profile, production=production_from_dict(production_data))


def study_from_dict(d: dict) -> StudyInput:
    d = _require_mapping(d, "study")
    schema = _check_schema(d)
    if "press" not in d:
        raise InvalidPressConfigurationError("Missing required object: press")
    return case_from_dict(d).to_study_input(press_from_dict(d["press"], schema_version=schema))


def press_to_dict(press: PressSpec, *, schema_version: str = CURRENT_SCHEMA_VERSION) -> dict:
    return {"schema_version": schema_version, "press": _press_dict_with_provenance(press)}


def case_to_dict(case: StudyCase, *, schema_version: str = CURRENT_SCHEMA_VERSION) -> dict:
    return case.to_dict(schema_version=schema_version)


def planning_case_to_dict(case: PlanningCase, *, schema_version: str = CURRENT_SCHEMA_VERSION) -> dict:
    return case.to_dict(schema_version=schema_version)


def study_to_dict(study: StudyInput, *, schema_version: str = CURRENT_SCHEMA_VERSION) -> dict:
    data = study.to_case().to_dict(schema_version=schema_version)
    data["press"] = _press_dict_with_provenance(study.press)
    return data


def load_study_json(path: str | Path) -> StudyInput:
    return study_from_dict(_read_json(path))


def load_case_json(path: str | Path) -> StudyCase:
    return case_from_dict(_read_json(path))


def load_planning_case_json(path: str | Path) -> PlanningCase:
    return planning_case_from_dict(_read_json(path))


def load_press_json(path: str | Path) -> PressSpec:
    data = _read_json(path)
    schema = _check_schema(data)
    if "press" in data:
        data = data["press"]
    return press_from_dict(data, schema_version=schema)


def _save_json(data: dict, path: str | Path, *, indent: int = 2) -> Path:
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, allow_nan=False)
            f.write("\n")
    except (IsADirectoryError, PermissionError, UnicodeError, OSError, ValueError) as exc:
        raise InputFileError(f"Cannot write JSON file {target}: {exc}") from exc
    return target


def save_press_json(press: PressSpec, path: str | Path, *, indent: int = 2) -> Path:
    return _save_json(press_to_dict(press), path, indent=indent)


def save_case_json(case: StudyCase, path: str | Path, *, indent: int = 2) -> Path:
    return _save_json(case_to_dict(case), path, indent=indent)


def save_planning_case_json(case: PlanningCase, path: str | Path, *, indent: int = 2) -> Path:
    return _save_json(planning_case_to_dict(case), path, indent=indent)


def save_study_json(study: StudyInput, path: str | Path, *, indent: int = 2) -> Path:
    return _save_json(study_to_dict(study), path, indent=indent)


def production_order_from_dict(d: dict) -> ProductionOrder:
    d = _require_mapping(d, "production_order")
    case_data = _require_mapping(d.get("case"), "production_order.case")
    request_data = _require_mapping(d.get("request"), "production_order.request")
    try:
        request = PlanningRequest(**request_data)
    except TypeError as exc:
        raise InvalidProductionSequenceError(f"Invalid production-order request: {exc}") from exc
    try:
        return ProductionOrder(
            order_id=d.get("order_id"),
            case=planning_case_from_dict(case_data),
            request=request,
        )
    except InvalidProductionSequenceError:
        raise


def production_order_to_dict(order: ProductionOrder) -> dict:
    if not isinstance(order, ProductionOrder):
        raise InvalidProductionSequenceError("production_order must be a ProductionOrder")
    case_data = order.case.to_dict()
    case_data.pop("schema_version", None)
    return {
        "order_id": order.order_id,
        "case": case_data,
        "request": order.request.to_dict(),
    }


def _parse_sequence_start_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InvalidProductionSequenceError("production_sequence.start_at must be an ISO-8601 string or null")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidProductionSequenceError(
            "production_sequence.start_at must be a valid ISO-8601 datetime"
        ) from exc


def production_sequence_from_dict(d: dict) -> tuple[PressSpec, tuple[ProductionOrder, ...], datetime | None]:
    d = _require_mapping(d, "production_sequence")
    schema = _check_schema(d)
    if "press" not in d:
        raise InvalidProductionSequenceError("production_sequence.press is required")
    raw_orders = d.get("orders")
    if not isinstance(raw_orders, list) or not raw_orders:
        raise InvalidProductionSequenceError("production_sequence.orders must be a non-empty JSON array")
    press = press_from_dict(_require_mapping(d["press"], "production_sequence.press"), schema_version=schema)
    orders = tuple(production_order_from_dict(item) for item in raw_orders)
    start_at = _parse_sequence_start_at(d.get("start_at"))
    return press, orders, start_at


def production_sequence_to_dict(
    press: PressSpec,
    orders: Iterable[ProductionOrder],
    *,
    start_at: datetime | None = None,
    schema_version: str = CURRENT_SCHEMA_VERSION,
) -> dict:
    if not isinstance(press, PressSpec):
        raise InvalidProductionSequenceError("production_sequence.press must be a PressSpec")
    if start_at is not None and not isinstance(start_at, datetime):
        raise InvalidProductionSequenceError("production_sequence.start_at must be a datetime or None")
    try:
        items = tuple(orders)
    except TypeError as exc:
        raise InvalidProductionSequenceError("production_sequence.orders must be iterable") from exc
    if not items:
        raise InvalidProductionSequenceError("production_sequence.orders must contain at least one order")
    return {
        "schema_version": schema_version,
        "press": _press_dict_with_provenance(press),
        "start_at": start_at.isoformat() if start_at is not None else None,
        "orders": [production_order_to_dict(order) for order in items],
    }


def load_production_sequence_json(path: str | Path) -> tuple[PressSpec, tuple[ProductionOrder, ...], datetime | None]:
    return production_sequence_from_dict(_read_json(path))


def save_production_sequence_json(
    press: PressSpec,
    orders: Iterable[ProductionOrder],
    path: str | Path,
    *,
    start_at: datetime | None = None,
    indent: int = 2,
) -> Path:
    return _save_json(
        production_sequence_to_dict(press, orders, start_at=start_at),
        path,
        indent=indent,
    )


def annual_demand_from_dict(d: dict) -> AnnualDemandSpec:
    d = _require_mapping(d, "annual_demand")
    if "annual_demand" in d:
        d = _require_mapping(d["annual_demand"], "annual_demand")
    try:
        return AnnualDemandSpec(**{k: v for k, v in d.items() if k != "schema_version"})
    except TypeError as exc:
        raise InvalidAnnualDemandError(f"Invalid annual demand configuration: {exc}") from exc


def annual_demand_to_dict(demand: AnnualDemandSpec, *, schema_version: str = CURRENT_SCHEMA_VERSION) -> dict:
    return {"schema_version": schema_version, "annual_demand": demand.to_dict()}


def load_annual_demand_json(path: str | Path) -> AnnualDemandSpec:
    data = _read_json(path)
    _check_schema(data)
    return annual_demand_from_dict(data)


def save_annual_demand_json(demand: AnnualDemandSpec, path: str | Path, *, indent: int = 2) -> Path:
    return _save_json(annual_demand_to_dict(demand), path, indent=indent)
