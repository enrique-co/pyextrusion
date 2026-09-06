from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from .api import calculate_process
from .errors import InvalidComparisonError
from .models import PlanningCase, PressSpec, ProcessResult
from .planning import PlanningRequest, PlanningResult, calculate_planning
from .sequence import (
    ProductionOrder,
    ProductionSequenceResult,
    calculate_production_sequence,
)


def _presses_tuple(presses: Iterable[PressSpec], *, minimum: int = 2) -> tuple[PressSpec, ...]:
    try:
        items = tuple(presses)
    except TypeError as exc:
        raise InvalidComparisonError("comparison presses must be an iterable of PressSpec objects") from exc
    if len(items) < minimum:
        raise InvalidComparisonError(
            f"comparison requires at least {minimum} presses"
        )
    for index, press in enumerate(items):
        if not isinstance(press, PressSpec):
            raise InvalidComparisonError(
                f"comparison presses[{index}] must be a PressSpec"
            )
    return items


@dataclass(frozen=True)
class ProcessComparisonResult:
    """Same quantity-free process evaluated independently on several presses.

    Results preserve the supplied press order. No ranking or winner is selected.
    """

    results: tuple[ProcessResult, ...]

    @property
    def press_count(self) -> int:
        return len(self.results)

    @property
    def supported_results(self) -> tuple[ProcessResult, ...]:
        return tuple(result for result in self.results if result.supported)

    @property
    def viable_results(self) -> tuple[ProcessResult, ...]:
        return tuple(result for result in self.results if result.viable)

    @property
    def supported_press_names(self) -> tuple[str, ...]:
        return tuple(result.press_name for result in self.supported_results)

    @property
    def viable_press_names(self) -> tuple[str, ...]:
        return tuple(result.press_name for result in self.viable_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_type": "process",
            "press_count": self.press_count,
            "supported_press_count": len(self.supported_results),
            "viable_press_count": len(self.viable_results),
            "supported_press_names": list(self.supported_press_names),
            "viable_press_names": list(self.viable_press_names),
            "automatic_winner": None,
            "results": [result.to_dict() for result in self.results],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class PlanningComparisonResult:
    """Same operational request evaluated independently on several presses."""

    request: PlanningRequest
    results: tuple[PlanningResult, ...]

    @property
    def press_count(self) -> int:
        return len(self.results)

    @property
    def fulfilled_results(self) -> tuple[PlanningResult, ...]:
        return tuple(result for result in self.results if result.request_fulfilled)

    @property
    def process_viable_results(self) -> tuple[PlanningResult, ...]:
        return tuple(result for result in self.results if result.process_viable)

    @property
    def fulfilled_press_names(self) -> tuple[str, ...]:
        return tuple(result.process.press_name for result in self.fulfilled_results)

    @property
    def process_viable_press_names(self) -> tuple[str, ...]:
        return tuple(result.process.press_name for result in self.process_viable_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_type": "planning",
            "request": self.request.to_dict(),
            "press_count": self.press_count,
            "process_viable_press_count": len(self.process_viable_results),
            "fulfilled_press_count": len(self.fulfilled_results),
            "process_viable_press_names": list(self.process_viable_press_names),
            "fulfilled_press_names": list(self.fulfilled_press_names),
            "automatic_winner": None,
            "results": [result.to_dict() for result in self.results],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class ProductionSequenceComparisonResult:
    """Same user-supplied production sequence evaluated on several presses.

    Each press receives the same orders in the same order. PyExtrusion does not
    allocate orders between presses, reorder them or declare an automatic winner.
    """

    results: tuple[ProductionSequenceResult, ...]

    @property
    def press_count(self) -> int:
        return len(self.results)

    @property
    def fully_resolved_results(self) -> tuple[ProductionSequenceResult, ...]:
        return tuple(result for result in self.results if result.all_orders_fulfilled)

    @property
    def fully_resolved_press_names(self) -> tuple[str, ...]:
        return tuple(result.press_name for result in self.fully_resolved_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_type": "production_sequence",
            "press_count": self.press_count,
            "fully_resolved_press_count": len(self.fully_resolved_results),
            "fully_resolved_press_names": list(self.fully_resolved_press_names),
            "automatic_winner": None,
            "results": [result.to_dict() for result in self.results],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


def compare_processes(
    presses: Iterable[PressSpec],
    case: PlanningCase,
) -> ProcessComparisonResult:
    """Evaluate one quantity-free PlanningCase on two or more presses."""
    press_tuple = _presses_tuple(presses)
    if not isinstance(case, PlanningCase):
        raise InvalidComparisonError("process comparison case must be a PlanningCase")
    return ProcessComparisonResult(
        tuple(calculate_process(press, case) for press in press_tuple)
    )


def compare_planning(
    presses: Iterable[PressSpec],
    case: PlanningCase,
    request: PlanningRequest,
) -> PlanningComparisonResult:
    """Evaluate one PlanningCase + PlanningRequest on two or more presses."""
    press_tuple = _presses_tuple(presses)
    if not isinstance(case, PlanningCase):
        raise InvalidComparisonError("planning comparison case must be a PlanningCase")
    if not isinstance(request, PlanningRequest):
        raise InvalidComparisonError("planning comparison request must be a PlanningRequest")
    return PlanningComparisonResult(
        request=request,
        results=tuple(calculate_planning(press, case, request) for press in press_tuple),
    )


def compare_production_sequences(
    presses: Iterable[PressSpec],
    orders: Iterable[ProductionOrder],
    *,
    start_at: datetime | None = None,
) -> ProductionSequenceComparisonResult:
    """Evaluate the exact same ordered production list on two or more presses."""
    press_tuple = _presses_tuple(presses)
    try:
        order_tuple = tuple(orders)
    except TypeError as exc:
        raise InvalidComparisonError(
            "sequence comparison orders must be an iterable of ProductionOrder objects"
        ) from exc
    if not order_tuple:
        raise InvalidComparisonError("sequence comparison requires at least one ProductionOrder")
    for index, order in enumerate(order_tuple):
        if not isinstance(order, ProductionOrder):
            raise InvalidComparisonError(
                f"sequence comparison orders[{index}] must be a ProductionOrder"
            )
    if start_at is not None and not isinstance(start_at, datetime):
        raise InvalidComparisonError("sequence comparison start_at must be a datetime or None")
    return ProductionSequenceComparisonResult(
        tuple(
            calculate_production_sequence(press, order_tuple, start_at=start_at)
            for press in press_tuple
        )
    )
