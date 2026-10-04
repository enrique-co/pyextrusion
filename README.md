# PyExtrusion

[![CI](https://github.com/enrique-co/pyextrusion/actions/workflows/ci.yml/badge.svg)](https://github.com/enrique-co/pyextrusion/actions/workflows/ci.yml)
[![Documentation](https://github.com/enrique-co/pyextrusion/actions/workflows/docs.yml/badge.svg)](https://github.com/enrique-co/pyextrusion/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/pyextrusion.svg)](https://pypi.org/project/pyextrusion/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)


**Engineering calculation toolkit for aluminium extrusion**

Version: **0.19.0** — 2026-10-03. Reference: [tag v0.19.0](https://github.com/enrique-co/pyextrusion/tree/v0.19.0), commit `9f7f4b495c63ba671e7412fa76e655dc068216d4`.

0.19.0 adds `trim_total_per_billet_m`, explicit legacy migration, and corrected positive-trim multibillet final-saw events, including partial pulls. Read the [trim contract and migration guide](docs/user-guide/trim-topology.md) before migrating sequential-pull data. New examples below use the canonical total. Retain the original legacy file and migrate with a verified family; do not mechanically rename `front_scrap_m` in existing p=2 data.

Version 0.18.0 corrects `butt_mm` as physical residual thickness inside the container: butt mass uses the container section, then converts once to incoming-billet equivalent length. Existing physical mm inputs and the measured incoming-billet coefficient override remain supported. Calculated lengths, losses and feasibility may differ from 0.17.0; see the [changelog](CHANGELOG.md).

PyExtrusion is a deterministic Python toolkit for evaluating aluminium profiles on **direct extrusion presses**. The same calculation engine is available through Python, CLI and JSON workflows.

PyExtrusion includes a source-traced engineering layer, basic deterministic economics and physical downstream saw-kerf accounting. The engineering models keep their scope explicit: the implemented pressure/force result is an **equivalent-axisymmetric baseline**, not a final porthole-die force prediction, and the thermal models are analytical/source-term baselines rather than a production-grade exit-temperature predictor.

## Three working areas

- **Production & Planning** — billet sizing, extrusion geometry, productivity,
  multi-billet processes, operational planning, sequences and multi-press
  comparison.
- **Engineering** — AA6063/AA6060 constitutive models, modified Feltham mean
  strain rate, Zener-Hollomon, flow stress, equivalent-axisymmetric mechanical
  baselines and bounded thermal tools.
- **Economics** — recurring production cost, material/scrap economics,
  tooling/development cost and sales-margin calculations.

## What changed in 0.19.0

- Defines total trim per incoming billet and divides it across sequential pulls.
- Provides explicit legacy migration, without silent input precedence.
- Counts final-saw events per actual positive-trim billet contribution, including a partial last pull.
- Exposes separate final-saw, internal-transition, puller-saw and billet-saw counters; commercial `cuts` remain distinct.
- Keeps the physical butt contract and bounded Engineering/Economics models unchanged.

## Retained from 0.18.0

- Corrects physical butt mass and equivalent incoming-billet length without changing the physical input values or redefining upsetting.
- Adds `AA6060` and `AA6063` as identical-object aliases of the existing source-traced constitutive models, preserving scientific names and provenance.
- Integrates the public Engineering section and separate Engineering/Economics API examples into the documentation.
- Retains the existing pressure, rheology, thermal and economics equations; no new alloy dataset or registry is introduced.
- Keeps shaped-section, bridge/porthole pressure corrections, complete transient thermal reconstruction and production-grade exit-temperature prediction outside the current model.

## Installation

From PyPI:

```bash
python -m pip install pyextrusion==0.19.0
```

From a locally built release wheel:

```bash
python -m pip install pyextrusion-0.19.0-py3-none-any.whl
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
        trim_total_per_billet_m=2,
    ),
)

result = calculate_case(press, case)

print(result.recommended_configuration)
print(result.billet.recommended_length_mm)
print(result.production.billets_per_pull)
print(result.productivity.real_net_kg_h)
```

All numerical examples are synthetic. `trim_total_per_billet_m=2` means 2 m total per incoming billet, not 2 m per pull. With two sequential pulls, each contribution receives 1 m. Inspect `result.process.trim_per_pull_m` for the selected full pull and the separate `result.production.*_saw_events` counters for the actual order.

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
        trim_total_per_billet_m=2,
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

- `k_billets_1_profile`: one continuous pull formed from one or more billets; `k` is resolved using physical table occupancy within each candidate, while selection remains billet-first;
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
- modeled startup, complexity, physical butt, total trim and saw losses;
- technical dead time and extrusion timing;
- nominal, real gross and real net productivity;
- geometric and productive utilisation indicators;
- annual-demand normalisation and an explicit optional 10% supplement;
- operational planning and time-window capacity calculations;
- continuous technical calculation of user-supplied order sequences;
- JSON persistence, validation and multi-press comparison;
- source-traced engineering baselines for hot-working rheology, equivalent-axisymmetric pressure/force and limited thermal analysis;
- basic deterministic production economics.

## Model boundary

PyExtrusion 0.19.0 models **direct aluminium extrusion**. It does not perform full industrial scheduling or complete extrusion-force, thermal, metallurgical, die-life or plant-resource prediction.

The mechanical result is `F_baseline`, an equivalent-axisymmetric baseline. A
comparison `F_reserve = F_press - F_baseline` is only a screening indicator; it is not
available hydraulic capacity, guaranteed remaining capacity, a safety margin, force available for a porthole
die or a prediction of the real die load.

The productivity index is orientative. It is not a physical quantity and must not be used alone as the final industrial selection criterion.

## Documentation

The public documentation is organised into:

- **User Guide** — task-oriented usage;
- **Engineering** — public analytical models and explicit interpretation limits;
- **Technical Reference** — selected engineering basis and formulas;
- **API Reference** — production, Engineering, Economics, JSON, CLI, result fields and errors;
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
