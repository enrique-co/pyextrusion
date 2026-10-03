# Installation and first steps

This checkout is **0.19.0 UNRELEASED CANDIDATE**. Install its local wheel to evaluate the candidate; PyPI installation below refers to published software, not this unuploaded candidate. Examples retaining `front_scrap_m` are legacy inputs; read [the trim migration guide](trim-topology.md) before changing them.

### Requirements

PyExtrusion requires **Python 3.10 or newer**.

### Install PyExtrusion

From PyPI:

```bash
python -m pip install pyextrusion
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

The local candidate output should identify PyExtrusion 0.19.0 and UNRELEASED CANDIDATE.

### Recommended: use a virtual environment

#### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install pyextrusion
```

#### Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install pyextrusion
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
        front_scrap_m=2,
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

PyExtrusion does not create fractional billets. The resulting number of manufactured bars can therefore be slightly above the requested target.

---
