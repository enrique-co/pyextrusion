"""Input contract for canonical billet trim and the explicit legacy fields."""
from ._strict import require_number
from .errors import InvalidProductionInputError


def validate_trim_inputs(front, total, multi, path="process"):
    """None means absent; even an explicit legacy zero conflicts with total."""
    if total is not None and (front is not None or multi is not None):
        raise InvalidProductionInputError(
            f"{path}.trim_total_per_billet_m cannot be combined with legacy "
            "front_scrap_m or multi_billet_front_scrap_m; migrate explicitly"
        )
    values = []
    for name, value in (("front_scrap_m", front), ("trim_total_per_billet_m", total),
                        ("multi_billet_front_scrap_m", multi)):
        values.append(None if value is None else require_number(
            value, f"{path}.{name}", InvalidProductionInputError, minimum=0.0
        ))
    return tuple(values)
