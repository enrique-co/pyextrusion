import math

import pytest

from pyextrusion.economics import (
    BasicCostSpec,
    BasicEconomicResult,
    EconomicProductionBasis,
    calculate_basic_economics,
)


def _example_costs(**changes):
    values = {
        "press_hour_cost": 200.0,
        "maintenance_hour_cost": 20.0,
        "labor_hour_cost": 30.0,
        "raw_material_cost_per_kg": 3.0,
        "scrap_processing_cost_per_kg": 0.2,
        "scrap_sale_value_per_kg": 1.5,
        "good_product_sale_value_per_kg": 5.0,
        "target_profit_margin_pct": 20.0,
        "die_cost": 2000.0,
        "extra_tooling_cost": 500.0,
        "currency": "EUR",
    }
    values.update(changes)
    return BasicCostSpec(**values)


def _example_production(**changes):
    values = {
        "production_time_h": 2.0,
        "good_kg_manufactured": 900.0,
        "revenue_good_kg": 800.0,
        "scrap_kg": 100.0,
    }
    values.update(changes)
    return EconomicProductionBasis(**values)


def test_basic_economics_breakdown_is_explicit_and_deterministic():
    result = calculate_basic_economics(_example_costs(), _example_production())

    assert result.costs.hourly_transformation_cost == pytest.approx(250.0)
    assert result.production.raw_material_input_kg == pytest.approx(1000.0)
    assert result.production.unsold_good_kg == pytest.approx(100.0)
    assert result.time_cost == pytest.approx(500.0)
    assert result.raw_material_cost == pytest.approx(3000.0)
    assert result.scrap_processing_cost == pytest.approx(20.0)
    assert result.scrap_recovery_value == pytest.approx(150.0)
    assert result.scrap_net_loss_cost == pytest.approx(170.0)
    assert result.recurring_cost == pytest.approx(3370.0)
    assert result.first_run_cost == pytest.approx(5870.0)


def test_tooling_is_separate_from_recurring_production_cost():
    result = calculate_basic_economics(_example_costs(), _example_production())

    assert result.costs.tooling_investment == pytest.approx(2500.0)
    assert result.first_run_cost - result.recurring_cost == pytest.approx(2500.0)


def test_overproduction_costs_money_without_automatically_creating_revenue():
    result = calculate_basic_economics(_example_costs(), _example_production())

    # 900 kg OK are manufactured, but only 800 kg carry sale value.
    assert result.revenue == pytest.approx(800.0 * 5.0)
    assert result.recurring_cost_per_revenue_kg == pytest.approx(3370.0 / 800.0)


def test_profit_margin_uses_sales_margin_not_markup():
    result = calculate_basic_economics(_example_costs(), _example_production())

    assert result.recurring_profit == pytest.approx(630.0)
    assert result.recurring_profit_margin_pct == pytest.approx(15.75)
    assert result.first_run_profit == pytest.approx(-1870.0)
    assert result.first_run_profit_margin_pct == pytest.approx(-46.75)

    # Target sale value uses cost / (1 - margin), not cost * (1 + margin).
    assert result.target_value_per_kg_recurring == pytest.approx((3370.0 / 800.0) / 0.8)
    assert result.target_value_per_kg_first_run == pytest.approx((5870.0 / 800.0) / 0.8)


def test_zero_maintenance_or_labor_cost_means_included_or_not_split_out():
    costs = _example_costs(maintenance_hour_cost=0.0, labor_hour_cost=0.0)

    assert costs.hourly_transformation_cost == pytest.approx(200.0)
    assert costs.maintenance_included_in_press_cost is True
    assert costs.labor_included_in_press_cost is True


def test_zero_sale_value_keeps_costing_valid_but_actual_margin_is_unavailable():
    result = calculate_basic_economics(
        _example_costs(good_product_sale_value_per_kg=0.0),
        _example_production(),
    )

    assert result.revenue == pytest.approx(0.0)
    assert result.recurring_profit_margin_pct is None
    assert result.first_run_profit_margin_pct is None
    assert result.target_value_per_kg_recurring > 0.0


def test_result_serialization_keeps_inputs_breakdown_and_results_separate():
    data = calculate_basic_economics(_example_costs(), _example_production()).to_dict()

    assert data["currency"] == "EUR"
    assert data["costs"]["hourly_transformation_cost"] == pytest.approx(250.0)
    assert data["production"]["raw_material_input_kg"] == pytest.approx(1000.0)
    assert data["breakdown"]["tooling_investment"] == pytest.approx(2500.0)
    assert data["results"]["recurring_cost"] == pytest.approx(3370.0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: BasicCostSpec(press_hour_cost=-1.0, raw_material_cost_per_kg=3.0),
        lambda: BasicCostSpec(press_hour_cost=True, raw_material_cost_per_kg=3.0),
        lambda: BasicCostSpec(press_hour_cost=100.0, raw_material_cost_per_kg="3"),
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            target_profit_margin_pct=100.0,
        ),
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            currency=" ",
        ),
        lambda: EconomicProductionBasis(
            production_time_h=-1.0,
            good_kg_manufactured=100.0,
            revenue_good_kg=100.0,
            scrap_kg=0.0,
        ),
        lambda: EconomicProductionBasis(
            production_time_h=1.0,
            good_kg_manufactured=0.0,
            revenue_good_kg=1.0,
            scrap_kg=0.0,
        ),
        lambda: EconomicProductionBasis(
            production_time_h=1.0,
            good_kg_manufactured=100.0,
            revenue_good_kg=0.0,
            scrap_kg=0.0,
        ),
        lambda: EconomicProductionBasis(
            production_time_h=1.0,
            good_kg_manufactured=100.0,
            revenue_good_kg=101.0,
            scrap_kg=0.0,
        ),
        lambda: EconomicProductionBasis(
            production_time_h=1.0,
            good_kg_manufactured=100.0,
            revenue_good_kg=100.0,
            scrap_kg=float("inf"),
        ),
    ],
)
def test_basic_economic_inputs_reject_invalid_values(factory):
    with pytest.raises(ValueError):
        factory()


def test_result_rejects_wrong_input_object_types():
    with pytest.raises(ValueError):
        BasicEconomicResult(costs="not-costs", production=_example_production())
    with pytest.raises(ValueError):
        BasicEconomicResult(costs=_example_costs(), production="not-production")


def test_extreme_finite_inputs_do_not_silently_produce_infinity():
    costs = _example_costs(press_hour_cost=1e308)
    production = _example_production(production_time_h=2.0)

    with pytest.raises(ValueError, match="finite range"):
        calculate_basic_economics(costs, production)


def test_break_even_value_matches_cost_per_revenue_kg():
    result = calculate_basic_economics(_example_costs(), _example_production())

    assert result.break_even_value_per_kg_recurring == pytest.approx(result.recurring_cost_per_revenue_kg)
    assert result.break_even_value_per_kg_first_run == pytest.approx(result.first_run_cost_per_revenue_kg)


def test_margin_formula_is_dimensionless_and_matches_manual_example():
    result = calculate_basic_economics(_example_costs(), _example_production())
    expected = (result.revenue - result.recurring_cost) / result.revenue * 100.0
    assert math.isclose(result.recurring_profit_margin_pct, expected, rel_tol=1e-12)
