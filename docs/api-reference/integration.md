# PyExtrusion integration guide — 0.16.0

PyExtrusion exposes one deterministic direct-extrusion engine through Python objects, JSON files and CLI commands. The calculations use the current PyExtrusion engine.

## 1. Press configuration

`table_length_m` is mandatory. Other common press values can be explicit or inferred from `nominal_size_in`.

```python
from pyextrusion import Press

press = Press(
    name="Line A",
    nominal_size_in=9,
    billet_diameter_mm=228,
    container_diameter_mm=236,
    billet_min_length_mm=500,
    billet_max_length_mm=1300,
    table_length_m=64,
    dead_time_sec=14,
    target_net_productivity_kg_h=2250,
)
```

Real plant values always take priority over inferred defaults.

## 2. Study/cotization case

```python
from pyextrusion import Profile, Production, StudyCase

case = StudyCase(
    profile=Profile(1.35, exits=2, profile_type="solid"),
    production=Production(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=1000,
        front_scrap_m=2,
        complexity="normal",
    ),
)
```

Calculate with:

```python
from pyextrusion import calculate_case
result = calculate_case(press, case)
```

Important structured outputs include:

```python
result.status.supported
result.geometry.extrusion_ratio
result.geometry.billets_per_pull
result.billet.recommended_length_mm
result.production.bars_per_billet
result.production.n_pulls
result.scrap.total_kg
result.productivity.real_net_kg_h
result.productivity.productivity_index
```

## 3. Billet-first and multi-billet semantics

PyExtrusion first selects the **longest feasible billet**. Only then does it calculate:

```text
billets_per_pull = floor(table_length / segment_length_per_billet)
```

It never reduces cuts merely to fit more billets on the table.

The multi-billet family is `k_billets_1_profile`; `k` is dynamic and may be greater than 3. The reverse case is deliberately limited: `1_billet_2_profiles` is supported, but 3+ profiles per billet are reported as unsupported.

For a multi-billet continuous pull, puller and final-saw operations are counted per pull. A final partial pull is modelled when the order billet count is not a multiple of `billets_per_pull`.

## 4. Planning API — quantity-free process architecture

A planning process should not contain a fictitious order quantity:

```python
from pyextrusion import PlanningCase, Process, Profile

process_case = PlanningCase(
    profile=Profile(1.35, exits=2, profile_type="solid"),
    process=Process(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        front_scrap_m=2,
        complexity="normal",
    ),
)
```

Evaluate the process independently from demand:

```python
from pyextrusion import calculate_process

process = calculate_process(press, process_case)
print(process.billet_length_mm)
print(process.bars_per_billet)
print(process.billets_per_pull)
```

Then provide the operational request separately:

```python
from pyextrusion import PlanningRequest, calculate_planning

plan = calculate_planning(press, process_case, PlanningRequest.bars(300))
calculate_planning(press, process_case, PlanningRequest.kg(2500))
calculate_planning(press, process_case, PlanningRequest.metres(1800))
calculate_planning(press, process_case, PlanningRequest.billets(20))
calculate_planning(press, process_case, PlanningRequest.hours(2))
```

For application integration, `plan.process` is the quantity-free `ProcessResult`; `plan.calculation` is the concrete order-level `CalculationResult` when at least one complete billet is planned.

`StudyCase` remains accepted by `calculate_planning()` only as a compatibility bridge and emits a deprecation warning.

## 5. Production-sequence API

For a user-defined list of orders:

```python
from pyextrusion import ProductionOrder, calculate_production_sequence

orders = [
    ProductionOrder("OF-001", process_case, PlanningRequest.bars(300)),
    ProductionOrder("OF-002", process_case, PlanningRequest.billets(20)),
]

sequence = calculate_production_sequence(press, orders)
```

The list order is preserved exactly. Sequence time is the sum of the individual planning times; PyExtrusion inserts no setup, die-change, waiting or calendar assumptions. Optional `start_at=<datetime>` adds theoretical clock timestamps only.

Capacity-window requests (`minutes`/`hours`) remain standalone planning queries and are not accepted as production-sequence order quantities.


## 6. Multi-press comparison

The same technical definition can be evaluated independently on two or more presses:

```python
from pyextrusion import compare_processes, compare_planning, compare_production_sequences

process_comparison = compare_processes([press_a, press_b, press_c], process_case)
planning_comparison = compare_planning(
    [press_a, press_b, press_c],
    process_case,
    PlanningRequest.bars(300),
)
sequence_comparison = compare_production_sequences(
    [press_a, press_b, press_c],
    orders,
)
```

The press list order is preserved. Every press receives the same process/request, and sequence comparison gives every press the complete same order list in the same order. PyExtrusion does not rank presses, declare a winner, distribute orders or balance workload.

## 7. Immutable adjustments

```python
faster = process_case.with_process(exit_speed_m_min=26)
three_exit = process_case.with_profile(exits=3)
```

Existing study cases retain:

```python
case.with_production(exit_speed_m_min=26)
case.with_profile(exits=3)
case.replace(exits=3, exit_speed_m_min=22)
```

## 8. JSON

Schema `1.1` is the current write format. Schemas `0.2` through `1.0` remain readable.

```python
from pyextrusion import (
    save_case_json,
    save_planning_case_json,
    save_press_json,
)

save_press_json(press, "press.json")
save_case_json(case, "case.json")
save_planning_case_json(process_case, "planning_case.json")
```

Production-sequence JSON can be loaded/saved with:

```python
from pyextrusion import load_production_sequence_json, save_production_sequence_json

save_production_sequence_json(press, orders, "production_sequence.json")
press2, orders2, start_at2 = load_production_sequence_json("production_sequence.json")
```

A planning-case JSON contains `profile` + `process`; no order quantity is required.

## 9. Model area distinction

Do not substitute billet area for container area:

- **container bore area** → extrusion ratio and ram speed;
- **actual billet area / kg-per-mm** → material mass, billet length and billet-related losses.

## 10. Result discovery and errors

```bash
pyextrusion fields
pyextrusion field production.billets_per_pull
pyextrusion errors
```

Use `result.supported` to distinguish an unsupported model scenario from a physically non-viable supported scenario.
