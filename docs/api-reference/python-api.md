# Python API

## Main objects

```python
from pyextrusion import (
    Press,
    Profile,
    Production,
    StudyCase,
    Process,
    PlanningCase,
    PlanningRequest,
)
```

### `Press`

Describes one direct extrusion press. `table_length_m` is mandatory.

### `Profile`

Describes profile linear weight, exits, profile type and optional explicit section.

### `Production`

Study/cotization input including the requested bar quantity.

### `Process`

Alias for `ProcessSpec`. Describes process conditions **without** a production quantity.

### `PlanningCase`

Combines `Profile + ProcessSpec` for quantity-independent process/planning calculations.

## Standard calculation

```python
from pyextrusion import calculate_case
result = calculate_case(press, study_case)
```

Important flat compatibility attributes remain available, while structured blocks are preferred for new integrations:

```python
result.status.supported
result.status.viable
result.geometry.extrusion_ratio
result.geometry.cuts
result.geometry.cuts_per_pull
result.geometry.billets_per_pull
result.billet.recommended_length_mm
result.production.bars_per_billet
result.production.bars_per_pull
result.production.n_pulls
result.scrap.fixed_pct
result.productivity.real_net_kg_h
result.productivity.productivity_index
result.timing.total_hours
```

## Supported versus viable

```python
if not result.supported:
    print(result.unsupported_reason)
elif not result.viable:
    print(result.warnings)
```

A process requiring 3+ profiles per billet is currently a controlled **unsupported** case, not an automatically extrapolated configuration.

## Billet-first configuration fields

```python
result.recommended_configuration
result.cuts
result.billets_per_pull
result.profiles_per_billet
result.cuts_per_pull
result.bars_per_pull
```

`k_billets_1_profile` can have any physically permitted `billets_per_pull`. `1_billet_2_profiles` has `profiles_per_billet == 2` and `billets_per_pull == 1`.

## Speed input

Use one speed input per process. Standard usage supplies exit/profile speed:

```python
Production(exit_speed_m_min=24, cut_length_mm=7000, bars_requested=300)
```

Alternatively, supply ram speed:

```python
production = Production.from_ram_speed(
    ram_speed_mm_s=0.70,
    cut_length_mm=7000,
    bars_requested=300,
)
```

`Process.from_ram_speed(...)` is available for quantity-free planning cases. PyExtrusion derives exit speed from container area and total profile area. Supplying both ram and exit speed is rejected as ambiguous.

## Strict industrial inputs

Structural counts (`exits`, manual `cuts`, bars and billets) are strict positive integers. Numeric strings, booleans, NaN and Infinity are rejected. A value such as `cut_length_mm=7` is **not** interpreted as 7 metres; it is rejected because the supported cut range is 1000-15000 mm.

## Quantity-free process evaluation

```python
from pyextrusion import calculate_process

process = calculate_process(press, planning_case)
```

Useful process-level outputs:

```python
process.viable
process.supported
process.recommended_configuration
process.cuts
process.bars_per_billet
process.billets_per_pull
process.bars_per_pull
process.billet_length_mm
process.recommended_billet_length_mm
process.table_occupancy_length_m
process.extrusion_ratio
process.exit_speed_m_min
process.ram_speed_mm_s
process.extrusion_time_per_billet_min
```

`ProcessResult` contains no requested bars, billets, kg or time window.

## Planning

```python
from pyextrusion import calculate_planning, PlanningRequest

plan = calculate_planning(press, planning_case, PlanningRequest.bars(300))
```

Requests:

```python
PlanningRequest.bars(300)
PlanningRequest.kg(2500)
PlanningRequest.metres(1800)
PlanningRequest.billets(20)
PlanningRequest.minutes(90)
PlanningRequest.hours(2)
```

Useful outputs:

```python
plan.process_supported
plan.process_viable
plan.request_fulfilled
plan.planned_billets
plan.planned_bars
plan.planned_good_m
plan.planned_good_kg
plan.billets_per_pull
plan.planned_pulls
plan.time_used_min
plan.time_remaining_min
plan.planned_fixed_scrap_kg
plan.planned_total_scrap_kg
plan.planned_total_scrap_pct
plan.process.billet_length_mm
```

## Immutable adjustments

```python
planning_case.with_profile(exits=3)
planning_case.with_process(exit_speed_m_min=26)

study_case.with_profile(exits=3)
study_case.with_production(exit_speed_m_min=26)
study_case.replace(exits=3, exit_speed_m_min=26)
```

## Result field discovery

```python
from pyextrusion import list_fields, describe_field

for field in list_fields():
    print(field.path, field.unit)

print(describe_field("production.billets_per_pull"))
```

Dotted access is also supported:

```python
result.value("productivity.real_net_kg_h")
result["production.billets_per_pull"]
result.select("geometry.extrusion_ratio", "productivity.real_net_kg_h")
```

## Production sequences

```python
from pyextrusion import ProductionOrder, calculate_production_sequence

orders = [
    ProductionOrder("OF-001", planning_case, PlanningRequest.bars(300)),
    ProductionOrder("OF-002", planning_case, PlanningRequest.billets(20)),
]

sequence = calculate_production_sequence(press, orders)
```

PyExtrusion preserves the supplied order exactly and inserts no setup or waiting time.

Useful outputs:

```python
sequence.orders
sequence.all_orders_fulfilled
sequence.unresolved_order_ids
sequence.total_planned_billets
sequence.total_planned_bars
sequence.total_planned_good_kg
sequence.total_scrap_kg
sequence.total_press_time_min

sequence.orders[0].duration_min
sequence.orders[0].cumulative_start_min
sequence.orders[0].cumulative_end_min
sequence.orders[0].planning
```

An optional Python `datetime` `start_at` adds theoretical clock timestamps without applying a plant calendar.

## Multi-press comparison

```python
from pyextrusion import compare_processes, compare_planning, compare_production_sequences

processes = compare_processes([press_a, press_b], planning_case)
plans = compare_planning([press_a, press_b], planning_case, PlanningRequest.bars(300))
sequences = compare_production_sequences([press_a, press_b], orders)
```

The new comparison APIs require at least two presses, preserve press order, use identical inputs on every press and never declare an automatic winner. See [Multi-press comparison](../user-guide/compare-presses.md).
