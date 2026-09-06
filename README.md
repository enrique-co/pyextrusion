# PyExtrusion

[![CI](https://github.com/enrique-co/pyextrusion/actions/workflows/ci.yml/badge.svg)](https://github.com/enrique-co/pyextrusion/actions/workflows/ci.yml)
[![Documentation](https://github.com/enrique-co/pyextrusion/actions/workflows/docs.yml/badge.svg)](https://github.com/enrique-co/pyextrusion/actions/workflows/docs.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)


**Engineering calculation toolkit for aluminium extrusion**

Current release candidate: **0.16.0**.

PyExtrusion is a deterministic Python toolkit for evaluating aluminium profiles on **direct extrusion presses**. The same calculation engine is available through Python, CLI and JSON workflows.

Version 0.16.0 adds multi-press comparison across quantity-free process calculations, single-order planning and production sequences. The direct-extrusion mathematics and the v0.15.0 production-sequence timing model are unchanged.

## What changed in 0.16.0

- Adds `compare_processes(presses, PlanningCase)`.
- Adds `compare_planning(presses, PlanningCase, PlanningRequest)`.
- Adds `compare_production_sequences(presses, orders, start_at=None)`.
- Adds `ProcessComparisonResult`, `PlanningComparisonResult` and `ProductionSequenceComparisonResult`.
- Requires two or more presses for the comparison APIs.
- Applies identical technical inputs to every press and preserves the user-supplied press order.
- Applies the same production-order list, in the same order, to every press in sequence comparisons.
- Performs no multi-press allocation, load balancing, automatic reordering or automatic winner selection.
- Adds human-readable comparison tables and strict JSON results.
- Adds CLI commands `compare-process`, `compare-planning` and `compare-sequence`.
- Adds stable `PX1013 InvalidComparison`.
- Keeps JSON input schema `1.1`; the comparison layer reuses existing press, planning-case and sequence inputs.

## Installation

From PyPI after publication:

```bash
python -m pip install pyextrusion
```

From a local release wheel:

```bash
python -m pip install pyextrusion-0.16.0-py3-none-any.whl
```

## Quick calculation

```python
from pyextrusion import Press, Profile, Production, StudyCase, calculate_case

press = Press(
    name="Example 8-inch press",
    nominal_size_in=8,
    table_length_m=54,
)

case = StudyCase(
    profile=Profile(1.35, exits=2, profile_type="solid"),
    production=Production(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=1000,
        front_scrap_m=2,
    ),
)

result = calculate_case(press, case)

print(result.recommended_configuration)
print(result.billet.recommended_length_mm)
print(result.production.billets_per_pull)
print(result.productivity.real_net_kg_h)
```

`table_length_m` is mandatory. Billet/container geometry, billet limits, dead time, saw kerfs and a reference productivity target can be inferred from `nominal_size_in`; real plant values supplied by the user always take priority.

## Quantity-free process definition for planning

```python
from pyextrusion import (
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    Profile,
    calculate_planning,
    calculate_process,
)

planning_case = PlanningCase(
    profile=Profile(1.35, exits=2, profile_type="solid"),
    process=Process(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        front_scrap_m=2,
        complexity="normal",
    ),
)

process = calculate_process(press, planning_case)
print(process.billet_length_mm, process.bars_per_billet)

plan = calculate_planning(press, planning_case, PlanningRequest.bars(300))
capacity = calculate_planning(press, planning_case, PlanningRequest.hours(2))
```

Planning works with complete billets. A request may be expressed in bars, kg, metres, billets, minutes or hours. The annual optional 10% supplement is not applied implicitly to an operational planning request.

## Continuous production sequences

```python
from datetime import datetime
from pyextrusion import ProductionOrder, calculate_production_sequence

orders = [
    ProductionOrder("OF-001", planning_case, PlanningRequest.bars(300)),
    ProductionOrder("OF-002", planning_case, PlanningRequest.billets(20)),
    ProductionOrder("OF-003", planning_case, PlanningRequest.kg(2500)),
]

sequence = calculate_production_sequence(
    press,
    orders,
    start_at=datetime(2026, 9, 7, 5, 0),
)

print(sequence.total_press_time_min)
print(sequence.orders[0].cumulative_end_min)
```

The returned timeline is **continuous technical press time only**. The supplied list is never reordered and PyExtrusion does not estimate setup or waiting time between orders.

## Multi-press comparison

```python
from pyextrusion import (
    compare_planning,
    compare_processes,
    compare_production_sequences,
)

process_cmp = compare_processes([press_a, press_b, press_c], planning_case)
plan_cmp = compare_planning(
    [press_a, press_b, press_c],
    planning_case,
    PlanningRequest.bars(300),
)
sequence_cmp = compare_production_sequences(
    [press_a, press_b, press_c],
    orders,
)
```

PyExtrusion returns results in the same order as the supplied presses. It does **not** rank them or declare a winner. A sequence comparison gives every press the complete same order list; it does not distribute work between presses.

## Supported production geometry

The current model supports:

- `k_billets_1_profile`: one continuous pull formed from one or more billets; `k` is calculated dynamically after billet optimisation;
- `1_billet_2_profiles`: one billet produces two complete sequential pulls.

A scenario requiring **3 or more complete sequential profiles from one billet is not supported** and is reported explicitly through support-status fields.

## Engineering model

Publicly documented calculations include:

- profile section from linear weight;
- extrusion ratio from **container-bore area**;
- ram speed from volume constancy;
- billet mass and kg/mm from actual billet geometry or a measured mass override;
- billet-first cut/billet optimisation;
- dynamic billet-on-billet continuous pulls;
- modeled startup, complexity, butt, front-scrap and saw losses;
- technical dead time and extrusion timing;
- nominal, real gross and real net productivity;
- geometric and productive utilisation indicators;
- annual-demand normalisation and an explicit optional 10% supplement;
- operational planning and time-window capacity calculations;
- continuous technical calculation of user-supplied order sequences;
- JSON persistence, validation and multi-press comparison.

## Model boundary

PyExtrusion 0.16.0 models **direct aluminium extrusion**. It does not perform full industrial scheduling or complete extrusion-force, thermal, metallurgical, die-life or plant-resource prediction.

The productivity index is orientative. It is not a physical quantity and must not be used alone as the final industrial selection criterion.

## Documentation

The public documentation is organised into:

- **User Guide** — task-oriented usage;
- **Technical Reference** — selected engineering basis and formulas;
- **API Reference** — Python, JSON, CLI, result fields and errors;
- **Examples** — practical workflows;
- **About** — project, citation, licence and changelog.

MkDocs source is included under `docs/` and configured by `mkdocs.yml`. The documentation site is intended for **https://pyextrusion.com**.

- Documentation: https://pyextrusion.com
- Source repository: https://github.com/enrique-co/pyextrusion
- Issue tracker: https://github.com/enrique-co/pyextrusion/issues

## Project identity

- Project: **PyExtrusion**
- Author: **Enrique Calvo Ordonez**
- Website: https://pyextrusion.com
- License: **Apache-2.0**
