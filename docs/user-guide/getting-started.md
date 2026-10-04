# Installation and first steps

This guide covers **PyExtrusion 0.19.0**. The synthetic example below uses canonical total trim per incoming billet. For older input files, follow [explicit legacy migration](trim-topology.md#legacy-api-and-json-migration).

### Requirements

PyExtrusion requires **Python 3.10 or newer**.

### Install PyExtrusion

From PyPI:

```bash
python -m pip install pyextrusion==0.19.0
```

When validating a locally built release artifact instead, install that wheel
explicitly:

```bash
python -m pip install pyextrusion-0.19.0-py3-none-any.whl
```

Verify the installation:

```bash
pyextrusion info
```

The output should identify PyExtrusion 0.19.0 and RELEASED.

### Recommended: use a virtual environment

#### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install pyextrusion==0.19.0
```

#### Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install pyextrusion==0.19.0
```

### Your first PyExtrusion objects

A normal operational calculation is built from four ideas:

```text
Press
  +
Profile
  +
Process
  =
PlanningCase
```

A quantity is then added separately through a `PlanningRequest`.

Example imports:

```python
from pyextrusion import (
    Press,
    Profile,
    Process,
    PlanningCase,
    PlanningRequest,
    calculate_process,
    calculate_planning,
)
```

### First complete example

```python
from pyextrusion import (
    Press,
    Profile,
    Process,
    PlanningCase,
    PlanningRequest,
    calculate_planning,
)

press = Press(
    name="Example 8-inch press",
    nominal_size_in=8,
    table_length_m=54,
)

case = PlanningCase(
    profile=Profile(
        linear_weight_kg_m=1.35,
        exits=2,
        profile_type="solid",
    ),
    process=Process(
        exit_speed_m_min=24,
        cut_length_mm=7000,
        trim_total_per_billet_m=2,
        complexity="normal",
    ),
)

plan = calculate_planning(
    press,
    case,
    PlanningRequest.bars(300),
)

print(plan.planned_billets)
print(plan.planned_bars)
print(plan.planned_good_kg)
print(plan.time_used_min)
```

This asks a simple question:

> How many complete billets are required to produce at least 300 finished bars, and what are the resulting production quantities and technical press time?

The reserve of 2 m is a **total per incoming billet**: a two-pull billet receives 1 m per sequential contribution. It is not front-only scrap or predicted charge-weld extent. The result separates commercial cuts from physical saw events; see [trim topology](trim-topology.md).

PyExtrusion does not create fractional billets. The resulting number of manufactured bars can therefore be slightly above the requested target.

---
