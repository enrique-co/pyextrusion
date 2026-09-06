# Define a profile and process

PyExtrusion deliberately separates the **profile** from the **process conditions**.

### Profile

A `Profile` describes the section being extruded.

```python
from pyextrusion import Profile

profile = Profile(
    linear_weight_kg_m=1.35,
    exits=2,
    profile_type="solid",
)
```

#### Required profile information

- `linear_weight_kg_m`: linear weight of **one exit**, in kg/m;
- `exits`: number of die exits;
- `profile_type`: physical family of the profile.

#### Supported profile types

| User value | Meaning | Internal family |
|---|---|---|
| `solid` | Solid profile | solid |
| `plate` | Plate / flat solid | solid |
| `hollow` | Hollow profile | hollow |
| `tubular` | Tube / tubular profile | hollow |

The profile type is required. PyExtrusion does not guess it.

#### Exits are strict integers

Valid:

```text
1
2
3
4
```

Invalid:

```text
2.5
"2"
True
```

### Process

A `Process` describes **how the profile is extruded**, not how much will be produced.

```python
from pyextrusion import Process

process = Process(
    exit_speed_m_min=24,
    cut_length_mm=7000,
    front_scrap_m=2,
    complexity="normal",
)
```

#### Main process inputs

- exit/profile speed;
- cut length;
- front scrap;
- complexity;
- optional manual number of cuts;
- optional butt override;
- optional special multi-billet front scrap.

### Important process ranges

| Input | Supported range / rule |
|---|---|
| Cut length | 1000 to 15000 mm |
| Exit/profile speed | 1 to 100 m/min |
| Front scrap | 0 or more; must remain compatible with table length |
| Complexity | `normal`, `medium`, `high` |

PyExtrusion never guesses units. For example:

```python
cut_length_mm=7
```

means **7 mm**, not 7 m, and is rejected.

### Enter ram speed instead of exit speed

If your plant works naturally with ram speed, you can provide it as the speed input:

```python
process = Process.from_ram_speed(
    ram_speed_mm_s=0.70,
    cut_length_mm=7000,
    front_scrap_m=2,
    complexity="normal",
)
```

PyExtrusion then derives the corresponding profile exit speed from the press/profile geometry.

Do not supply both ram speed and exit speed for the same process. They are alternative inputs.

### Build a PlanningCase

```python
from pyextrusion import PlanningCase

case = PlanningCase(
    profile=profile,
    process=process,
)
```

This object contains no production quantity. The same `PlanningCase` can therefore be reused for 300 bars, 20 billets, 2500 kg or a two-hour capacity check.

---
