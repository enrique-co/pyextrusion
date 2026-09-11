# Basic economics

PyExtrusion includes a deliberately simple deterministic economics layer under `pyextrusion.economics`.
It consumes explicit time, mass and commercial assumptions; it does **not** estimate electricity use, taxes, financing, depreciation, transport, packaging or other omitted business costs.

## Inputs

`BasicCostSpec` accepts:

- press cost per hour;
- maintenance cost per hour;
- labour cost per hour;
- raw-material cost per kg;
- scrap-processing cost per kg;
- scrap sale/recovery value per kg;
- sale value per kg of revenue-generating good product;
- target profit margin as a percentage of sales;
- die cost;
- extra-tooling cost;
- a currency label.

When maintenance or labour hourly cost is zero, PyExtrusion treats that item as not split out separately. By project convention the caller may use this to indicate that it is already included in the press hourly cost.

## Production basis

`EconomicProductionBasis` keeps four quantities explicit:

- `production_time_h`;
- `good_kg_manufactured`;
- `revenue_good_kg`;
- `scrap_kg`.

The distinction between manufactured OK mass and revenue-generating OK mass is intentional. If a whole-billet calculation manufactures more good product than the order requires, the extra mass still consumes material and press time but does not create revenue unless the caller explicitly includes it in `revenue_good_kg`.

Raw-material input is defined as:

\[
m_{input}=m_{OK,manufactured}+m_{scrap}
\]

## Cost equations

Hourly transformation cost is:

\[
C_h=C_{press,h}+C_{maintenance,h}+C_{labour,h}
\]

Time cost is:

\[
C_{time}=t\,C_h
\]

Raw-material cost is:

\[
C_{material}=m_{input}\,C_{material/kg}
\]

Scrap processing and recovery are:

\[
C_{scrap,processing}=m_{scrap}\,C_{processing/kg}
\]

\[
R_{scrap}=m_{scrap}\,V_{scrap/kg}
\]

Recurring production cost is:

\[
C_{recurring}=C_{time}+C_{material}+C_{scrap,processing}-R_{scrap}
\]

Tooling investment is kept separate:

\[
I_{tooling}=C_{die}+C_{extra\ tooling}
\]

and first-run cost is:

\[
C_{first}=C_{recurring}+I_{tooling}
\]

No tooling amortisation schedule is assumed.

## Revenue and margin

Revenue is:

\[
Revenue=m_{revenue\ good}\,V_{good/kg}
\]

Profit margin uses the sales-margin convention:

\[
Margin=\frac{Revenue-Cost}{Revenue}
\]

This is not markup on cost.

For a target margin `M` expressed as a fraction of sales, the target sale value is:

\[
V_{target/kg}=\frac{C_{per\ revenue\ kg}}{1-M}
\]

## Example

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
print(result.target_value_per_kg_recurring)
```

## Boundaries

This layer is an accounting calculation over caller-supplied assumptions. It does not prove that a quoted sale value can be achieved, that all produced OK mass can be sold, or that omitted costs are negligible. It performs no currency conversion and does not infer plant overheads.
