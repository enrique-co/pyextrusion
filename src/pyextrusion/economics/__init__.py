"""Basic deterministic cost and margin calculations for PyExtrusion.

This package consumes explicit time, mass and commercial assumptions. It does
not estimate electricity, taxes, financing, depreciation, transport, packaging
or any other omitted business cost.
"""

from .basic import (
    BasicCostSpec,
    BasicEconomicResult,
    EconomicProductionBasis,
    calculate_basic_economics,
)

__all__ = [
    "BasicCostSpec",
    "BasicEconomicResult",
    "EconomicProductionBasis",
    "calculate_basic_economics",
]
