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
- number of die-development trials / press setups;
- flat cost assigned to each die-development trial / press setup;
- optional one-time tooling amount charged to the customer;
- a currency label.

When maintenance or labour hourly cost is zero, PyExtrusion treats that item as not split out separately. By project convention the caller may use this to indicate that it is already included in the press hourly cost.

`die_trial_count` and `die_trial_cost_each` provide a simple way to include repeated die-development trials. The resulting surcharge is:

\[
C_{trials}=N_{trials}\,C_{trial}
\]

This is a flat caller-supplied cost. Do not use it to duplicate trial time or trial material costs that have already been included elsewhere in the economic scenario.

`customer_tooling_charge` defaults to zero. PyExtrusion never assumes that the customer pays the die, extra tooling or trial costs. When an amount is supplied, it is treated as one-time first-run revenue only.

## Production basis

`EconomicProductionBasis` keeps four quantities explicit:

- `production_time_h`;
- `good_kg_manufactured`;
- `revenue_good_kg`;
- `scrap_kg`.

The distinction between manufactured OK mass and revenue-generating OK mass is intentional, but PyExtrusion does not encode customer-specific overproduction rules. The caller decides the accepted commercial quantity. For a strict customer, `revenue_good_kg` may equal the requested quantity; for a customer that accepts some overproduction, it may be higher, up to `good_kg_manufactured`.

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
I_{tooling}=C_{die}+C_{extra\ tooling}+C_{trials}
\]

and first-run cost is:

\[
C_{first}=C_{recurring}+I_{tooling}
\]

No tooling amortisation schedule is assumed.

## Revenue and margin

Product revenue is:

\[
Revenue_{product}=m_{revenue\ good}\,V_{good/kg}
\]

When the customer pays a separate one-time tooling amount:

\[
Revenue_{first}=Revenue_{product}+Charge_{tooling,customer}
\]

The recurring calculation uses product revenue only. The first-run calculation uses `Revenue_first`.

Profit margin uses the sales-margin convention:

\[
Margin=\frac{Revenue-Cost}{Revenue}
\]

This is not markup on cost.

For a target margin `M` expressed as a fraction of sales, recurring target sale value remains:

\[
V_{target/kg}=\frac{C_{recurring}/m_{revenue\ good}}{1-M}
\]

For the first run, a separately charged tooling amount reduces the product revenue still required to reach the same target margin.

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
    die_trial_count=3,
    die_trial_cost_each=250.0,
    customer_tooling_charge=0.0,
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
print(result.costs.die_trial_cost_total)
print(result.target_value_per_kg_first_run)
```

## Boundaries

This layer is an accounting calculation over caller-supplied assumptions. It does not decide which production excess a customer accepts, infer how many die trials occurred, or infer the real internal cost of a trial. It does not prove that a quoted sale value can be achieved or that omitted costs are negligible. It performs no currency conversion and does not infer plant overheads.
