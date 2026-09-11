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
        "die_trial_count": 0,
        "die_trial_cost_each": 0.0,
        "customer_tooling_charge": 0.0,
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


def test_die_trials_add_a_flat_development_surcharge_to_tooling():
    costs = _example_costs(die_trial_count=3, die_trial_cost_each=250.0)
    result = calculate_basic_economics(costs, _example_production())

    assert costs.die_trial_cost_total == pytest.approx(750.0)
    assert costs.tooling_investment == pytest.approx(3250.0)
    assert result.first_run_cost == pytest.approx(6620.0)
    assert result.recurring_cost == pytest.approx(3370.0)


def test_customer_tooling_charge_is_optional_first_run_revenue_only():
    costs = _example_costs(
        die_trial_count=2,
        die_trial_cost_each=250.0,
        customer_tooling_charge=2000.0,
    )
    result = calculate_basic_economics(costs, _example_production())

    assert result.product_revenue == pytest.approx(4000.0)
    assert result.revenue == pytest.approx(4000.0)  # compatibility alias
    assert result.first_run_revenue == pytest.approx(6000.0)
    assert result.recurring_profit == pytest.approx(630.0)
    assert result.first_run_cost == pytest.approx(6370.0)
    assert result.first_run_profit == pytest.approx(-370.0)
    assert result.first_run_profit_margin_pct == pytest.approx(-370.0 / 6000.0 * 100.0)


def test_first_run_break_even_and_target_product_value_credit_tooling_charge():
    costs = _example_costs(
        die_trial_count=2,
        die_trial_cost_each=250.0,
        customer_tooling_charge=2000.0,
        target_profit_margin_pct=20.0,
    )
    result = calculate_basic_economics(costs, _example_production())

    assert result.first_run_cost == pytest.approx(6370.0)
    assert result.first_run_cost_not_covered_by_tooling_charge == pytest.approx(4370.0)
    assert result.break_even_value_per_kg_first_run == pytest.approx(4370.0 / 800.0)
    expected_target_product_revenue = 6370.0 / 0.8 - 2000.0
    assert result.target_value_per_kg_first_run == pytest.approx(expected_target_product_revenue / 800.0)


def test_overproduction_revenue_is_caller_declared_not_business_rule_inferred():
    base = _example_costs()
    strict_customer = calculate_basic_economics(
        base,
        _example_production(good_kg_manufactured=900.0, revenue_good_kg=800.0),
    )
    customer_accepts_extra = calculate_basic_economics(
        base,
        _example_production(good_kg_manufactured=900.0, revenue_good_kg=895.0),
    )

    assert strict_customer.production.unsold_good_kg == pytest.approx(100.0)
    assert customer_accepts_extra.production.unsold_good_kg == pytest.approx(5.0)
    assert strict_customer.revenue == pytest.approx(800.0 * 5.0)
    assert customer_accepts_extra.revenue == pytest.approx(895.0 * 5.0)


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


def test_customer_tooling_charge_can_make_first_run_margin_available_without_product_price():
    result = calculate_basic_economics(
        _example_costs(good_product_sale_value_per_kg=0.0, customer_tooling_charge=7000.0),
        _example_production(),
    )

    assert result.recurring_profit_margin_pct is None
    assert result.first_run_revenue == pytest.approx(7000.0)
    assert result.first_run_profit_margin_pct is not None


def test_result_serialization_keeps_inputs_breakdown_and_results_separate():
    data = calculate_basic_economics(
        _example_costs(die_trial_count=2, die_trial_cost_each=100.0, customer_tooling_charge=500.0),
        _example_production(),
    ).to_dict()

    assert data["currency"] == "EUR"
    assert data["costs"]["hourly_transformation_cost"] == pytest.approx(250.0)
    assert data["costs"]["die_trial_count"] == 2
    assert data["production"]["raw_material_input_kg"] == pytest.approx(1000.0)
    assert data["breakdown"]["die_trial_cost_total"] == pytest.approx(200.0)
    assert data["breakdown"]["tooling_investment"] == pytest.approx(2700.0)
    assert data["breakdown"]["customer_tooling_charge"] == pytest.approx(500.0)
    assert data["results"]["recurring_cost"] == pytest.approx(3370.0)
    assert data["results"]["first_run_revenue"] == pytest.approx(4500.0)


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
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            die_trial_count=-1,
        ),
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            die_trial_count=True,
        ),
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            die_trial_count=1.5,
        ),
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            die_trial_cost_each=-1.0,
        ),
        lambda: BasicCostSpec(
            press_hour_cost=100.0,
            raw_material_cost_per_kg=3.0,
            customer_tooling_charge=-1.0,
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


def test_extreme_trial_cost_does_not_silently_produce_infinity():
    costs = _example_costs(die_trial_count=2, die_trial_cost_each=1e308)

    with pytest.raises(ValueError, match="finite range"):
        calculate_basic_economics(costs, _example_production())


def test_break_even_value_matches_cost_per_revenue_kg_when_no_tooling_charge():
    result = calculate_basic_economics(_example_costs(), _example_production())

    assert result.break_even_value_per_kg_recurring == pytest.approx(result.recurring_cost_per_revenue_kg)
    assert result.break_even_value_per_kg_first_run == pytest.approx(result.first_run_cost_per_revenue_kg)


def test_margin_formula_is_dimensionless_and_matches_manual_example():
    result = calculate_basic_economics(_example_costs(), _example_production())
    expected = (result.revenue - result.recurring_cost) / result.revenue * 100.0
    assert math.isclose(result.recurring_profit_margin_pct, expected, rel_tol=1e-12)
