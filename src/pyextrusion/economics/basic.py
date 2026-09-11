from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .._strict import require_int, require_number


def _nonnegative(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0)
    assert result is not None
    return result


def _positive(value: float, field: str) -> float:
    result = require_number(value, field, ValueError, minimum=0.0, exclusive_minimum=True)
    assert result is not None
    return result


def _finite_result(value: float, field: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field} is outside the representable finite range")
    return value


def _nonempty_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class BasicCostSpec:
    """User-supplied basic economic assumptions for one production scenario.

    The model is deliberately simple and contains no electricity model,
    depreciation schedule, financing, tax, transport, packaging or accounting
    allocation rules.

    ``maintenance_hour_cost`` and ``labor_hour_cost`` may be zero. By project
    convention, zero means that the caller considers that item already included
    in ``press_hour_cost`` or does not wish to split it out separately.

    ``die_trial_count`` represents separate die-development trials / press
    setups. ``die_trial_cost_each`` is a flat incremental cost assigned to each
    such trial. It is caller-supplied and must not silently duplicate trial time
    or material costs already included elsewhere in the scenario.

    ``customer_tooling_charge`` is the one-time amount actually charged to the
    customer for die/tooling development. It defaults to zero: PyExtrusion never
    assumes that the customer pays the die, extra tooling or trial costs.
    """

    press_hour_cost: float
    raw_material_cost_per_kg: float
    maintenance_hour_cost: float = 0.0
    labor_hour_cost: float = 0.0
    scrap_processing_cost_per_kg: float = 0.0
    scrap_sale_value_per_kg: float = 0.0
    good_product_sale_value_per_kg: float = 0.0
    target_profit_margin_pct: float = 0.0
    die_cost: float = 0.0
    extra_tooling_cost: float = 0.0
    die_trial_count: int = 0
    die_trial_cost_each: float = 0.0
    customer_tooling_charge: float = 0.0
    currency: str = "EUR"

    def __post_init__(self) -> None:
        for field_name in (
            "press_hour_cost",
            "raw_material_cost_per_kg",
            "maintenance_hour_cost",
            "labor_hour_cost",
            "scrap_processing_cost_per_kg",
            "scrap_sale_value_per_kg",
            "good_product_sale_value_per_kg",
            "die_cost",
            "extra_tooling_cost",
            "die_trial_cost_each",
            "customer_tooling_charge",
        ):
            object.__setattr__(self, field_name, _nonnegative(getattr(self, field_name), field_name))

        trial_count = require_int(self.die_trial_count, "die_trial_count", ValueError, minimum=0)
        object.__setattr__(self, "die_trial_count", trial_count)

        margin = require_number(
            self.target_profit_margin_pct,
            "target_profit_margin_pct",
            ValueError,
            minimum=0.0,
            maximum=100.0,
        )
        assert margin is not None
        if margin >= 100.0:
            raise ValueError("target_profit_margin_pct must be < 100")
        object.__setattr__(self, "target_profit_margin_pct", margin)
        object.__setattr__(self, "currency", _nonempty_text(self.currency, "currency"))

    @property
    def hourly_transformation_cost(self) -> float:
        return _finite_result(
            self.press_hour_cost + self.maintenance_hour_cost + self.labor_hour_cost,
            "hourly transformation cost",
        )

    @property
    def die_trial_cost_total(self) -> float:
        return _finite_result(self.die_trial_count * self.die_trial_cost_each, "die trial cost total")

    @property
    def tooling_investment(self) -> float:
        return _finite_result(
            self.die_cost + self.extra_tooling_cost + self.die_trial_cost_total,
            "tooling investment",
        )

    @property
    def maintenance_included_in_press_cost(self) -> bool:
        return self.maintenance_hour_cost == 0.0

    @property
    def labor_included_in_press_cost(self) -> bool:
        return self.labor_hour_cost == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "press_hour_cost": self.press_hour_cost,
            "maintenance_hour_cost": self.maintenance_hour_cost,
            "labor_hour_cost": self.labor_hour_cost,
            "hourly_transformation_cost": self.hourly_transformation_cost,
            "maintenance_included_in_press_cost": self.maintenance_included_in_press_cost,
            "labor_included_in_press_cost": self.labor_included_in_press_cost,
            "raw_material_cost_per_kg": self.raw_material_cost_per_kg,
            "scrap_processing_cost_per_kg": self.scrap_processing_cost_per_kg,
            "scrap_sale_value_per_kg": self.scrap_sale_value_per_kg,
            "good_product_sale_value_per_kg": self.good_product_sale_value_per_kg,
            "target_profit_margin_pct": self.target_profit_margin_pct,
            "die_cost": self.die_cost,
            "extra_tooling_cost": self.extra_tooling_cost,
            "die_trial_count": self.die_trial_count,
            "die_trial_cost_each": self.die_trial_cost_each,
            "die_trial_cost_total": self.die_trial_cost_total,
            "tooling_investment": self.tooling_investment,
            "customer_tooling_charge": self.customer_tooling_charge,
            "currency": self.currency,
        }


@dataclass(frozen=True)
class EconomicProductionBasis:
    """Mass and time basis for a basic economic calculation.

    ``good_kg_manufactured`` is the total OK mass physically manufactured.
    ``revenue_good_kg`` is the mass to which the sale value is applied. It may
    represent the exact order quantity, all manufactured OK mass, or an
    intermediate customer-accepted quantity. PyExtrusion deliberately does not
    encode customer-specific overproduction tolerances.

    ``revenue_good_kg`` must be <= manufactured OK mass. ``scrap_kg`` is the
    total metal mass treated as scrap/recoverable loss for the scenario. Raw
    material input is defined here as manufactured OK mass plus scrap mass.
    """

    production_time_h: float
    good_kg_manufactured: float
    revenue_good_kg: float
    scrap_kg: float

    def __post_init__(self) -> None:
        production_time = _nonnegative(self.production_time_h, "production_time_h")
        manufactured = _positive(self.good_kg_manufactured, "good_kg_manufactured")
        revenue_mass = _positive(self.revenue_good_kg, "revenue_good_kg")
        scrap = _nonnegative(self.scrap_kg, "scrap_kg")
        if revenue_mass > manufactured:
            raise ValueError("revenue_good_kg cannot exceed good_kg_manufactured")
        object.__setattr__(self, "production_time_h", production_time)
        object.__setattr__(self, "good_kg_manufactured", manufactured)
        object.__setattr__(self, "revenue_good_kg", revenue_mass)
        object.__setattr__(self, "scrap_kg", scrap)
        _finite_result(self.raw_material_input_kg, "raw material input mass")

    @property
    def raw_material_input_kg(self) -> float:
        return self.good_kg_manufactured + self.scrap_kg

    @property
    def unsold_good_kg(self) -> float:
        return self.good_kg_manufactured - self.revenue_good_kg

    def to_dict(self) -> dict[str, float]:
        return {
            "production_time_h": self.production_time_h,
            "good_kg_manufactured": self.good_kg_manufactured,
            "revenue_good_kg": self.revenue_good_kg,
            "unsold_good_kg": self.unsold_good_kg,
            "scrap_kg": self.scrap_kg,
            "raw_material_input_kg": self.raw_material_input_kg,
        }


@dataclass(frozen=True)
class BasicEconomicResult:
    """Derived basic production economics under explicit caller assumptions.

    Tooling is intentionally separated from recurrent production cost. The
    first-run result includes die, extra tooling and die-development trial costs
    once; no amortization schedule is assumed.

    Product revenue and an optional customer tooling charge are kept separate.
    The latter applies only to the first-run economics.

    Profit margin follows the sales-margin convention::

        margin = (revenue - cost) / revenue

    It is not a markup-on-cost calculation.
    """

    costs: BasicCostSpec
    production: EconomicProductionBasis

    def __post_init__(self) -> None:
        if not isinstance(self.costs, BasicCostSpec):
            raise ValueError("costs must be a BasicCostSpec")
        if not isinstance(self.production, EconomicProductionBasis):
            raise ValueError("production must be an EconomicProductionBasis")
        # Force evaluation of the main outputs so non-finite arithmetic is
        # rejected at construction time rather than leaking into serialization.
        for field_name, value in (
            ("time cost", self.time_cost),
            ("raw material cost", self.raw_material_cost),
            ("scrap processing cost", self.scrap_processing_cost),
            ("scrap recovery value", self.scrap_recovery_value),
            ("recurring cost", self.recurring_cost),
            ("first-run cost", self.first_run_cost),
            ("product revenue", self.product_revenue),
            ("first-run revenue", self.first_run_revenue),
        ):
            _finite_result(value, field_name)

    @property
    def time_cost(self) -> float:
        return self.production.production_time_h * self.costs.hourly_transformation_cost

    @property
    def raw_material_cost(self) -> float:
        return self.production.raw_material_input_kg * self.costs.raw_material_cost_per_kg

    @property
    def scrap_processing_cost(self) -> float:
        return self.production.scrap_kg * self.costs.scrap_processing_cost_per_kg

    @property
    def scrap_recovery_value(self) -> float:
        return self.production.scrap_kg * self.costs.scrap_sale_value_per_kg

    @property
    def scrap_net_loss_cost(self) -> float:
        """Economic penalty attributable to each kg classified as scrap.

        This diagnostic includes the raw material tied up in scrap, scrap
        processing, and the recovered sale value. It is already represented in
        ``recurring_cost`` and must not be added to it again.
        """
        return self.production.scrap_kg * (
            self.costs.raw_material_cost_per_kg
            + self.costs.scrap_processing_cost_per_kg
            - self.costs.scrap_sale_value_per_kg
        )

    @property
    def recurring_cost(self) -> float:
        return (
            self.time_cost
            + self.raw_material_cost
            + self.scrap_processing_cost
            - self.scrap_recovery_value
        )

    @property
    def first_run_cost(self) -> float:
        return self.recurring_cost + self.costs.tooling_investment

    @property
    def recurring_cost_per_revenue_kg(self) -> float:
        return self.recurring_cost / self.production.revenue_good_kg

    @property
    def first_run_cost_per_revenue_kg(self) -> float:
        return self.first_run_cost / self.production.revenue_good_kg

    @property
    def product_revenue(self) -> float:
        return self.production.revenue_good_kg * self.costs.good_product_sale_value_per_kg

    @property
    def revenue(self) -> float:
        """Compatibility alias for product revenue only."""
        return self.product_revenue

    @property
    def first_run_revenue(self) -> float:
        return self.product_revenue + self.costs.customer_tooling_charge

    @property
    def recurring_profit(self) -> float:
        return self.product_revenue - self.recurring_cost

    @property
    def first_run_profit(self) -> float:
        return self.first_run_revenue - self.first_run_cost

    @staticmethod
    def _margin_pct(profit: float, revenue: float) -> float | None:
        if revenue <= 0.0:
            return None
        return _finite_result(profit / revenue * 100.0, "profit margin")

    @property
    def recurring_profit_margin_pct(self) -> float | None:
        return self._margin_pct(self.recurring_profit, self.product_revenue)

    @property
    def first_run_profit_margin_pct(self) -> float | None:
        return self._margin_pct(self.first_run_profit, self.first_run_revenue)

    @property
    def break_even_value_per_kg_recurring(self) -> float:
        return self.recurring_cost_per_revenue_kg

    @property
    def first_run_cost_not_covered_by_tooling_charge(self) -> float:
        return max(0.0, self.first_run_cost - self.costs.customer_tooling_charge)

    @property
    def break_even_value_per_kg_first_run(self) -> float:
        return self.first_run_cost_not_covered_by_tooling_charge / self.production.revenue_good_kg

    def _target_value_per_kg(self, cost_per_kg: float) -> float:
        margin_fraction = self.costs.target_profit_margin_pct / 100.0
        return _finite_result(cost_per_kg / (1.0 - margin_fraction), "target sale value per kg")

    @property
    def target_value_per_kg_recurring(self) -> float:
        return self._target_value_per_kg(self.recurring_cost_per_revenue_kg)

    @property
    def target_value_per_kg_first_run(self) -> float:
        margin_fraction = self.costs.target_profit_margin_pct / 100.0
        target_total_revenue = self.first_run_cost / (1.0 - margin_fraction)
        product_revenue_required = max(0.0, target_total_revenue - self.costs.customer_tooling_charge)
        return _finite_result(
            product_revenue_required / self.production.revenue_good_kg,
            "target first-run sale value per kg",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.costs.currency,
            "costs": self.costs.to_dict(),
            "production": self.production.to_dict(),
            "breakdown": {
                "time_cost": self.time_cost,
                "raw_material_cost": self.raw_material_cost,
                "scrap_processing_cost": self.scrap_processing_cost,
                "scrap_recovery_value": self.scrap_recovery_value,
                "scrap_net_loss_cost": self.scrap_net_loss_cost,
                "die_trial_cost_total": self.costs.die_trial_cost_total,
                "tooling_investment": self.costs.tooling_investment,
                "customer_tooling_charge": self.costs.customer_tooling_charge,
            },
            "results": {
                "recurring_cost": self.recurring_cost,
                "first_run_cost": self.first_run_cost,
                "recurring_cost_per_revenue_kg": self.recurring_cost_per_revenue_kg,
                "first_run_cost_per_revenue_kg": self.first_run_cost_per_revenue_kg,
                "product_revenue": self.product_revenue,
                "revenue": self.revenue,
                "first_run_revenue": self.first_run_revenue,
                "recurring_profit": self.recurring_profit,
                "first_run_profit": self.first_run_profit,
                "recurring_profit_margin_pct": self.recurring_profit_margin_pct,
                "first_run_profit_margin_pct": self.first_run_profit_margin_pct,
                "first_run_cost_not_covered_by_tooling_charge": self.first_run_cost_not_covered_by_tooling_charge,
                "break_even_value_per_kg_recurring": self.break_even_value_per_kg_recurring,
                "break_even_value_per_kg_first_run": self.break_even_value_per_kg_first_run,
                "target_value_per_kg_recurring": self.target_value_per_kg_recurring,
                "target_value_per_kg_first_run": self.target_value_per_kg_first_run,
            },
        }


def calculate_basic_economics(
    costs: BasicCostSpec,
    production: EconomicProductionBasis,
) -> BasicEconomicResult:
    """Calculate a simple, deterministic economic breakdown for one scenario."""
    return BasicEconomicResult(costs=costs, production=production)
