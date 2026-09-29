# Economics API

The deterministic economics interface is available from
`pyextrusion.economics`.

## Public objects

- `BasicCostSpec` — explicit hourly, material, scrap, tooling and commercial
  assumptions;
- `EconomicProductionBasis` — production time, manufactured good mass,
  revenue-generating good mass and scrap mass;
- `calculate_basic_economics()` — recurring and first-run cost, revenue and
  sales-margin calculation;
- `BasicEconomicResult` — structured result returned by the calculation.

## Complete example

```python
from pyextrusion.economics import (
    BasicCostSpec,
    EconomicProductionBasis,
    calculate_basic_economics,
)

costs = BasicCostSpec(
    press_hour_cost=200.0,
    maintenance_hour_cost=20.0,
    labor_hour_cost=30.0,
    raw_material_cost_per_kg=3.0,
    scrap_processing_cost_per_kg=0.20,
    scrap_sale_value_per_kg=1.50,
    good_product_sale_value_per_kg=5.00,
    target_profit_margin_pct=20.0,
    die_cost=2000.0,
    extra_tooling_cost=500.0,
    die_trial_count=3,
    die_trial_cost_each=250.0,
    currency="EUR",
)
production = EconomicProductionBasis(
    production_time_h=2.0,
    good_kg_manufactured=900.0,
    revenue_good_kg=800.0,
    scrap_kg=100.0,
)

result = calculate_basic_economics(costs, production)

print(result.recurring_cost)
print(result.first_run_cost)
print(result.recurring_profit_margin_pct)
print(result.target_value_per_kg_first_run)
```

All amounts and the currency label are supplied by the caller. The API does not
perform currency conversion or infer taxes, depreciation, financing, energy,
overheads, transport or customer acceptance of overproduction.

See [Basic economics](../user-guide/basic-economics.md) for calculation meaning
and boundaries.
