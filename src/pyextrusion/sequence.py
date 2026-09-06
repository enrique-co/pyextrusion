from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from ._strict import require_string
from .errors import InvalidProductionSequenceError
from .models import PlanningCase, PressSpec
from .planning import PlanningRequest, PlanningResult, calculate_planning, validate_planning_request

_SEQUENCE_REQUEST_MODES = {"bars", "kg", "m", "billets"}


@dataclass(frozen=True)
class ProductionOrder:
    """One explicit production order in a user-supplied sequence.

    A sequence order contains only an identifier, a quantity-free ``PlanningCase``
    and an explicit quantity ``PlanningRequest``. It intentionally contains no
    setup, die-change, waiting, calendar or resource-assumption fields.
    """

    order_id: str
    case: PlanningCase
    request: PlanningRequest

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "order_id",
            require_string(
                self.order_id,
                "sequence.order_id",
                InvalidProductionSequenceError,
            ),
        )
        if not isinstance(self.case, PlanningCase):
            raise InvalidProductionSequenceError(
                "sequence.case must be a PlanningCase; quantity-bearing StudyCase objects are not accepted in production sequences"
            )
        if not isinstance(self.request, PlanningRequest):
            raise InvalidProductionSequenceError(
                "sequence.request must be a PlanningRequest"
            )
        validate_planning_request(self.request)
        if self.request.mode not in _SEQUENCE_REQUEST_MODES:
            raise InvalidProductionSequenceError(
                "production-sequence orders must use bars, kg, m or billets; minutes/hours are capacity-window requests, not production-order quantities"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "case": self.case.to_dict(),
            "request": self.request.to_dict(),
        }


@dataclass(frozen=True)
class ProductionSequenceEntry:
    """Calculated position of one order in a continuous technical sequence."""

    index: int
    order: ProductionOrder
    planning: PlanningResult
    cumulative_start_min: float
    cumulative_end_min: float
    theoretical_start_at: datetime | None = None
    theoretical_end_at: datetime | None = None

    @property
    def order_id(self) -> str:
        return self.order.order_id

    @property
    def duration_min(self) -> float:
        return self.planning.time_used_min

    @property
    def planned_billets(self) -> int:
        return self.planning.planned_billets

    @property
    def planned_pulls(self) -> int:
        return self.planning.planned_pulls

    @property
    def planned_bars(self) -> int:
        return self.planning.planned_bars

    @property
    def planned_good_m(self) -> float:
        return self.planning.planned_good_m

    @property
    def planned_good_kg(self) -> float:
        return self.planning.planned_good_kg

    @property
    def planned_fixed_scrap_kg(self) -> float:
        return self.planning.planned_fixed_scrap_kg

    @property
    def planned_total_scrap_kg(self) -> float:
        return self.planning.planned_total_scrap_kg

    @property
    def request_fulfilled(self) -> bool:
        return self.planning.request_fulfilled

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "order_id": self.order_id,
            "request_fulfilled": self.request_fulfilled,
            "duration_min": self.duration_min,
            "cumulative_start_min": self.cumulative_start_min,
            "cumulative_end_min": self.cumulative_end_min,
            "theoretical_start_at": self.theoretical_start_at.isoformat() if self.theoretical_start_at is not None else None,
            "theoretical_end_at": self.theoretical_end_at.isoformat() if self.theoretical_end_at is not None else None,
            "planned_billets": self.planned_billets,
            "planned_pulls": self.planned_pulls,
            "planned_bars": self.planned_bars,
            "planned_good_m": self.planned_good_m,
            "planned_good_kg": self.planned_good_kg,
            "planned_fixed_scrap_kg": self.planned_fixed_scrap_kg,
            "planned_total_scrap_kg": self.planned_total_scrap_kg,
            "order": self.order.to_dict(),
            "planning": self.planning.to_dict(),
        }


@dataclass(frozen=True)
class ProductionSequenceResult:
    """Continuous technical press-time calculation for an ordered list."""

    press_name: str
    orders: tuple[ProductionSequenceEntry, ...]
    start_at: datetime | None
    theoretical_end_at: datetime | None
    all_orders_fulfilled: bool
    unresolved_order_ids: tuple[str, ...]
    total_planned_billets: int
    total_planned_pulls: int
    total_planned_bars: int
    total_planned_good_m: float
    total_planned_good_kg: float
    total_fixed_scrap_kg: float
    total_scrap_kg: float
    total_press_time_min: float
    warnings: tuple[str, ...] = ()

    @property
    def total_orders(self) -> int:
        return len(self.orders)

    @property
    def total_press_hours(self) -> float:
        return self.total_press_time_min / 60.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "press_name": self.press_name,
            "start_at": self.start_at.isoformat() if self.start_at is not None else None,
            "theoretical_end_at": self.theoretical_end_at.isoformat() if self.theoretical_end_at is not None else None,
            "total_orders": self.total_orders,
            "all_orders_fulfilled": self.all_orders_fulfilled,
            "unresolved_order_ids": list(self.unresolved_order_ids),
            "total_planned_billets": self.total_planned_billets,
            "total_planned_pulls": self.total_planned_pulls,
            "total_planned_bars": self.total_planned_bars,
            "total_planned_good_m": self.total_planned_good_m,
            "total_planned_good_kg": self.total_planned_good_kg,
            "total_fixed_scrap_kg": self.total_fixed_scrap_kg,
            "total_scrap_kg": self.total_scrap_kg,
            "total_press_time_min": self.total_press_time_min,
            "total_press_hours": self.total_press_hours,
            "warnings": list(self.warnings),
            "orders": [entry.to_dict() for entry in self.orders],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


def _timestamp_at(start_at: datetime, minutes: float, field: str) -> datetime:
    try:
        value = start_at + timedelta(minutes=minutes)
    except (OverflowError, ValueError) as exc:
        raise InvalidProductionSequenceError(
            f"{field} cannot be represented as a Python datetime for the supplied start_at"
        ) from exc
    return value


def calculate_production_sequence(
    press: PressSpec,
    orders: Iterable[ProductionOrder],
    *,
    start_at: datetime | None = None,
) -> ProductionSequenceResult:
    """Calculate a user-supplied order list in continuous technical press time.

    The input order is preserved exactly. No setup time, waiting time, die
    availability, shifts, maintenance, resource constraints or automatic
    sequencing logic are inserted. Consecutive fulfilled orders are therefore
    contiguous in cumulative technical press time.
    """

    if not isinstance(press, PressSpec):
        raise InvalidProductionSequenceError("sequence press must be a PressSpec")
    if start_at is not None and not isinstance(start_at, datetime):
        raise InvalidProductionSequenceError(
            "sequence.start_at must be a datetime or None"
        )

    try:
        items = tuple(orders)
    except TypeError as exc:
        raise InvalidProductionSequenceError(
            "sequence orders must be an iterable of ProductionOrder objects"
        ) from exc

    if not items:
        raise InvalidProductionSequenceError(
            "production sequence must contain at least one order"
        )

    entries: list[ProductionSequenceEntry] = []
    cumulative = 0.0

    for index, order in enumerate(items, start=1):
        if not isinstance(order, ProductionOrder):
            raise InvalidProductionSequenceError(
                f"sequence orders[{index - 1}] must be a ProductionOrder"
            )

        planning = calculate_planning(press, order.case, order.request)
        duration = planning.time_used_min
        if not math.isfinite(duration) or duration < 0:
            raise InvalidProductionSequenceError(
                f"sequence order {order.order_id!r} produced an invalid technical duration"
            )

        cumulative_start = cumulative
        cumulative_end = cumulative_start + duration
        if not math.isfinite(cumulative_end):
            raise InvalidProductionSequenceError(
                "sequence cumulative technical time is outside the supported finite numeric range"
            )

        theoretical_start = (
            _timestamp_at(start_at, cumulative_start, "sequence.theoretical_start_at")
            if start_at is not None
            else None
        )
        theoretical_end = (
            _timestamp_at(start_at, cumulative_end, "sequence.theoretical_end_at")
            if start_at is not None
            else None
        )

        entries.append(
            ProductionSequenceEntry(
                index=index,
                order=order,
                planning=planning,
                cumulative_start_min=cumulative_start,
                cumulative_end_min=cumulative_end,
                theoretical_start_at=theoretical_start,
                theoretical_end_at=theoretical_end,
            )
        )
        cumulative = cumulative_end

    unresolved = tuple(entry.order_id for entry in entries if not entry.request_fulfilled)
    warnings: list[str] = []
    if unresolved:
        warnings.append(
            "One or more orders could not be resolved. Unresolved orders remain in their original position and contribute 0 minutes to the continuous technical sequence."
        )
    warnings.append(
        "Sequence times are continuous technical press times only; no setup, waiting, die-preparation, calendar or external plant constraints are inserted."
    )

    total_good_m = math.fsum(entry.planned_good_m for entry in entries)
    total_good_kg = math.fsum(entry.planned_good_kg for entry in entries)
    total_fixed_scrap = math.fsum(entry.planned_fixed_scrap_kg for entry in entries)
    total_scrap = math.fsum(entry.planned_total_scrap_kg for entry in entries)
    numeric_totals = (total_good_m, total_good_kg, total_fixed_scrap, total_scrap, cumulative)
    if not all(math.isfinite(value) for value in numeric_totals):
        raise InvalidProductionSequenceError(
            "sequence aggregate result is outside the supported finite numeric range"
        )

    theoretical_end_at = (
        _timestamp_at(start_at, cumulative, "sequence.theoretical_end_at")
        if start_at is not None
        else None
    )

    return ProductionSequenceResult(
        press_name=press.name,
        orders=tuple(entries),
        start_at=start_at,
        theoretical_end_at=theoretical_end_at,
        all_orders_fulfilled=not unresolved,
        unresolved_order_ids=unresolved,
        total_planned_billets=sum(entry.planned_billets for entry in entries),
        total_planned_pulls=sum(entry.planned_pulls for entry in entries),
        total_planned_bars=sum(entry.planned_bars for entry in entries),
        total_planned_good_m=total_good_m,
        total_planned_good_kg=total_good_kg,
        total_fixed_scrap_kg=total_fixed_scrap,
        total_scrap_kg=total_scrap,
        total_press_time_min=cumulative,
        warnings=tuple(warnings),
    )
