from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorInfo:
    code: str
    name: str
    category: str
    description: str
    resolution: str
    cli_exit_code: int = 2


ERROR_CATALOG: dict[str, ErrorInfo] = {
    "PX1001": ErrorInfo(
        "PX1001", "InvalidPressConfiguration", "configuration",
        "The press configuration is missing required values or contains invalid values.",
        "Review the press JSON or PressSpec values and run `pyextrusion validate press.json`.",
    ),
    "PX1002": ErrorInfo(
        "PX1002", "InvalidProfileInput", "input",
        "The profile definition is missing required values or contains invalid values.",
        "Provide profile_type explicitly using solid, plate, hollow or tubular; also review linear weight, exits and optional section values.",
    ),
    "PX1003": ErrorInfo(
        "PX1003", "InvalidProductionInput", "input",
        "The production definition is missing required values or contains invalid values.",
        "Review speed, cut length, requested bars, scrap, cuts and manual overrides.",
    ),
    "PX1004": ErrorInfo(
        "PX1004", "UnknownResultField", "result",
        "A requested result field path does not exist in the public result-field catalog.",
        "Run `pyextrusion fields` or `pyextrusion field <path>` and use an exact documented field path.",
    ),
    "PX1005": ErrorInfo(
        "PX1005", "UnsupportedSchemaVersion", "schema",
        "The JSON schema_version is not supported by this PyExtrusion release.",
        "Use a supported schema version or migrate the file before loading it.",
    ),
    "PX1006": ErrorInfo(
        "PX1006", "InvalidAnnualDemand", "input",
        "The annual-demand definition is invalid.",
        "Use unit kg, m or bars and provide a value greater than zero.",
    ),
    "PX1007": ErrorInfo(
        "PX1007", "InputFileError", "file",
        "An input file cannot be read, is not valid JSON, or has an invalid top-level structure.",
        "Check the path and JSON syntax, then validate the file again.",
    ),
    "PX1008": ErrorInfo(
        "PX1008", "UnknownResultSection", "result",
        "A requested structured result section does not exist.",
        "Use one of status, geometry, billet, production, scrap, productivity, timing or process.",
    ),
    "PX1009": ErrorInfo(
        "PX1009", "InvalidResultSelection", "result",
        "A result selection request is empty or malformed.",
        "Provide at least one exact documented result field path.",
    ),
    "PX1010": ErrorInfo(
        "PX1010", "InvalidStudyAdjustment", "input",
        "A requested StudyCase adjustment uses an unknown or unsupported field name.",
        "Use `with_profile()`, `with_production()` or `replace()` with documented StudyCase input fields.",
    ),
    "PX1011": ErrorInfo(
        "PX1011", "InvalidPlanningRequest", "input",
        "The operational planning request is invalid.",
        "Use bars, kg, m, billets, minutes or hours with a positive value; bars and billets must be whole numbers.",
    ),
    "PX1012": ErrorInfo(
        "PX1012", "InvalidProductionSequence", "input",
        "A production-sequence definition is invalid.",
        "Provide at least one ProductionOrder using a PlanningCase and a bars, kg, m or billets PlanningRequest; sequence order is preserved and no external plant times are inferred.",
    ),
    "PX1013": ErrorInfo(
        "PX1013", "InvalidComparison", "input",
        "A multi-press comparison request is invalid.",
        "Provide at least two PressSpec objects and a supported process, planning or production-sequence comparison input.",
    ),
}


class PyExtrusionError(Exception):
    """Base class for documented PyExtrusion errors."""

    code = "PX0000"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None):
        info = ERROR_CATALOG.get(self.code)
        self.info = info
        self.details = details or {}
        self.message = message or (info.description if info else self.__class__.__name__)
        super().__init__(self.message)

    @property
    def name(self) -> str:
        return self.info.name if self.info else self.__class__.__name__

    @property
    def cli_exit_code(self) -> int:
        return self.info.cli_exit_code if self.info else 2

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class InvalidPressConfigurationError(PyExtrusionError, ValueError):
    code = "PX1001"


class InvalidProfileInputError(PyExtrusionError, ValueError):
    code = "PX1002"


class InvalidProductionInputError(PyExtrusionError, ValueError):
    code = "PX1003"


class UnknownResultFieldError(PyExtrusionError, KeyError):
    code = "PX1004"


class UnsupportedSchemaVersionError(PyExtrusionError, ValueError):
    code = "PX1005"


class InvalidAnnualDemandError(PyExtrusionError, ValueError):
    code = "PX1006"


class InputFileError(PyExtrusionError, ValueError):
    code = "PX1007"


class UnknownResultSectionError(PyExtrusionError, KeyError):
    code = "PX1008"


class InvalidResultSelectionError(PyExtrusionError, ValueError):
    code = "PX1009"


class InvalidStudyAdjustmentError(PyExtrusionError, ValueError):
    code = "PX1010"


class InvalidPlanningRequestError(PyExtrusionError, ValueError):
    code = "PX1011"


class InvalidProductionSequenceError(PyExtrusionError, ValueError):
    code = "PX1012"


class InvalidComparisonError(PyExtrusionError, ValueError):
    code = "PX1013"


def get_error_info(code: str) -> ErrorInfo:
    normalized = str(code).upper()
    if normalized not in ERROR_CATALOG:
        raise KeyError(f"Unknown PyExtrusion error code: {code}")
    return ERROR_CATALOG[normalized]


def list_error_info() -> tuple[ErrorInfo, ...]:
    return tuple(ERROR_CATALOG[code] for code in sorted(ERROR_CATALOG))
