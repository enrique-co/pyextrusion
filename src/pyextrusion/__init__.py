"""PyExtrusion - engineering calculation toolkit for aluminium extrusion."""
from ._meta import __author__, __description__, __license__, __title__, __url__, __version__
from .api import calculate_case, calculate_process, calculate_simple, compare_presses
from .comparison import (
    ProcessComparisonResult, PlanningComparisonResult, ProductionSequenceComparisonResult,
    compare_processes, compare_planning, compare_production_sequences,
)
from .demand import (
    AnnualDemandSpec, NormalizedAnnualDemand, AnnualCalculationResult,
    normalize_annual_demand, calculate_annual_demand,
)
from .planning import (
    PlanningMode, PlanningRequest, PlanningResult,
    validate_planning_request, calculate_planning,
)
from .sequence import (
    ProductionOrder, ProductionSequenceEntry, ProductionSequenceResult,
    calculate_production_sequence,
)
from .core import calculate, section_from_linear_weight, extrusion_ratio, extrusion_ratio_status, ram_speed
from .io import (
    case_from_dict,
    case_to_dict,
    load_case_json,
    load_press_json,
    load_study_json,
    press_from_dict,
    press_to_dict,
    process_from_dict,
    planning_case_from_dict,
    planning_case_to_dict,
    load_planning_case_json,
    save_planning_case_json,
    save_case_json,
    save_press_json,
    save_study_json,
    study_from_dict,
    study_to_dict,
    annual_demand_from_dict, annual_demand_to_dict,
    load_annual_demand_json, save_annual_demand_json,
    production_order_from_dict, production_order_to_dict,
    production_sequence_from_dict, production_sequence_to_dict,
    load_production_sequence_json, save_production_sequence_json,
)
from .models import (
    PressSpec, ProfileSpec, ProcessSpec, PlanningCase, ProductionSpec, StudyCase, StudyInput,
    CalculationResult, ProcessResult, ComparisonResult, ConfigurationResult,
    StatusResult, GeometryResult, BilletResult, ProductionResult, ScrapResult,
    ProductivityResult, TimingResult, ProcessTraceResult,
    SawSpec, ButtRule, ProfileType, CanonicalProfileType, PROFILE_TYPE_ALIASES,
    PROFILE_TYPE_VALID_VALUES, normalize_profile_type,
)
from .reporting import (
    format_annual_result, format_comparison, format_press, format_result,
    format_planning_result, format_production_sequence,
    format_process_comparison, format_planning_comparison,
    format_production_sequence_comparison,
)
from .fields import FieldInfo, FIELD_GLOSSARY, RESULT_SECTIONS, describe_field, list_fields
from .errors import (
    ErrorInfo, ERROR_CATALOG, PyExtrusionError, InvalidPressConfigurationError,
    InvalidProfileInputError, InvalidProductionInputError, UnknownResultFieldError,
    UnsupportedSchemaVersionError, InvalidAnnualDemandError, InputFileError,
    UnknownResultSectionError, InvalidResultSelectionError, InvalidStudyAdjustmentError,
    InvalidPlanningRequestError, InvalidProductionSequenceError, InvalidComparisonError,
    get_error_info, list_error_info,
)
from .validation import (
    ValidationMessage,
    validate_case,
    validate_case_json,
    validate_planning_case,
    validate_planning_case_json,
    validate_press,
    validate_press_json,
    validate_study,
    validate_study_json,
    validate_annual_demand, validate_annual_demand_json,
    validate_production_sequence_json,
)

Press = PressSpec
Profile = ProfileSpec
Process = ProcessSpec
Production = ProductionSpec

__all__ = [
    "calculate", "calculate_case", "calculate_process", "calculate_simple", "compare_presses",
    "compare_processes", "compare_planning", "compare_production_sequences",
    "normalize_annual_demand", "calculate_annual_demand", "calculate_planning",
    "validate_planning_request", "calculate_production_sequence",
    "section_from_linear_weight", "extrusion_ratio", "extrusion_ratio_status", "ram_speed",
    "Press", "Profile", "Process", "Production", "PressSpec", "ProfileSpec", "ProcessSpec", "PlanningCase", "ProductionSpec",
    "StudyCase", "StudyInput", "CalculationResult", "ProcessResult", "ComparisonResult", "ConfigurationResult",
    "StatusResult", "GeometryResult", "BilletResult", "ProductionResult", "ScrapResult",
    "ProductivityResult", "TimingResult", "ProcessTraceResult",
    "SawSpec", "ButtRule", "ProfileType", "CanonicalProfileType", "PROFILE_TYPE_ALIASES",
    "PROFILE_TYPE_VALID_VALUES", "normalize_profile_type",
    "AnnualDemandSpec", "NormalizedAnnualDemand", "AnnualCalculationResult",
    "PlanningMode", "PlanningRequest", "PlanningResult",
    "ProductionOrder", "ProductionSequenceEntry", "ProductionSequenceResult",
    "ProcessComparisonResult", "PlanningComparisonResult", "ProductionSequenceComparisonResult",
    "load_press_json", "load_case_json", "load_planning_case_json", "load_study_json",
    "save_press_json", "save_case_json", "save_planning_case_json", "save_study_json",
    "load_annual_demand_json", "save_annual_demand_json",
    "load_production_sequence_json", "save_production_sequence_json",
    "press_from_dict", "process_from_dict", "planning_case_from_dict", "case_from_dict", "study_from_dict", "annual_demand_from_dict",
    "production_order_from_dict", "production_sequence_from_dict",
    "press_to_dict", "planning_case_to_dict", "case_to_dict", "study_to_dict", "annual_demand_to_dict",
    "production_order_to_dict", "production_sequence_to_dict",
    "format_press", "format_result", "format_comparison", "format_annual_result", "format_planning_result", "format_production_sequence",
    "format_process_comparison", "format_planning_comparison", "format_production_sequence_comparison",
    "FieldInfo", "FIELD_GLOSSARY", "RESULT_SECTIONS", "describe_field", "list_fields",
    "ErrorInfo", "ERROR_CATALOG", "PyExtrusionError", "InvalidPressConfigurationError",
    "InvalidProfileInputError", "InvalidProductionInputError", "UnknownResultFieldError",
    "UnsupportedSchemaVersionError", "InvalidAnnualDemandError", "InputFileError",
    "UnknownResultSectionError", "InvalidResultSelectionError", "InvalidStudyAdjustmentError",
    "InvalidPlanningRequestError", "InvalidProductionSequenceError", "InvalidComparisonError",
    "get_error_info", "list_error_info",
    "ValidationMessage", "validate_press", "validate_case", "validate_planning_case", "validate_study",
    "validate_press_json", "validate_case_json", "validate_planning_case_json", "validate_study_json",
    "validate_annual_demand", "validate_annual_demand_json", "validate_production_sequence_json",
    "__title__", "__version__", "__description__", "__author__", "__license__", "__url__",
]
