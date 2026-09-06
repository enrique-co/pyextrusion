from __future__ import annotations

import math
from typing import Any, TypeVar

E = TypeVar("E", bound=Exception)


def _raise(exc_type: type[E], message: str) -> None:
    raise exc_type(message)


def require_number(
    value: Any,
    field: str,
    exc_type: type[E],
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
    allow_none: bool = False,
) -> float | None:
    if value is None:
        if allow_none:
            return None
        _raise(exc_type, f"{field} is required")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise(exc_type, f"{field} must be a number, not {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        _raise(exc_type, f"{field} must be a finite number")
    if minimum is not None:
        if exclusive_minimum:
            if not result > minimum:
                _raise(exc_type, f"{field} must be > {minimum:g}")
        elif result < minimum:
            _raise(exc_type, f"{field} must be >= {minimum:g}")
    if maximum is not None and result > maximum:
        _raise(exc_type, f"{field} must be <= {maximum:g}")
    return result


def require_int(
    value: Any,
    field: str,
    exc_type: type[E],
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    allow_none: bool = False,
) -> int | None:
    if value is None:
        if allow_none:
            return None
        _raise(exc_type, f"{field} is required")
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(exc_type, f"{field} must be an integer")
    if minimum is not None and value < minimum:
        _raise(exc_type, f"{field} must be >= {minimum}")
    if maximum is not None and value > maximum:
        _raise(exc_type, f"{field} must be <= {maximum}")
    return value


def require_bool(value: Any, field: str, exc_type: type[E]) -> bool:
    if not isinstance(value, bool):
        _raise(exc_type, f"{field} must be true or false")
    return value


def require_string(value: Any, field: str, exc_type: type[E], *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        _raise(exc_type, f"{field} must be a string")
    if nonempty and not value.strip():
        _raise(exc_type, f"{field} must not be empty")
    return value


def require_kerf(value: Any, field: str, exc_type: type[E]) -> float:
    result = require_number(value, field, exc_type, minimum=0.0)
    assert result is not None
    if result == 0.0:
        return 0.0
    if result < 3.0 or result > 10.0:
        _raise(exc_type, f"{field} must be 0 mm or between 3 and 10 mm")
    return result


def finite_product(a: float, b: float, field: str, exc_type: type[E]) -> float:
    value = a * b
    if not math.isfinite(value):
        _raise(exc_type, f"{field} is outside the supported finite numeric range")
    return value
