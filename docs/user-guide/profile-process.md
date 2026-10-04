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
    trim_total_per_billet_m=2,
    complexity="normal",
)
```

#### Main process inputs

- exit/profile speed;
- cut length;
- total trim/reject reserve per incoming billet (`trim_total_per_billet_m`);
- complexity;
- optional manual number of cuts;
- optional butt override (`butt_mm`: physical residual thickness inside the container);
- explicit legacy front-scrap inputs for older data only; do not combine with canonical trim.

For `p` sequential pulls, `trim_per_contribution = trim_total_per_billet_m / p`. This total is not front-only scrap, trim per pull or a metallurgical charge-weld prediction. The output `trim_per_pull_m` sums all contributions in a **full** pull; it is not always the per-contribution value.

See [trim topology and legacy migration](trim-topology.md). In particular, a synthetic legacy `front_scrap_m=0.6` with two sequential pulls becomes canonical total `1.2`, not `0.6`.

The butt input and plant butt rules retain physical mm values. Defaults remain 15 mm for solid/plate and 20 mm for hollow/tubular. No numeric input migration is required. Butt mass uses density and the container-bore section. The engine converts this mass to an equivalent incoming-billet length internally, once. `billet_kg_per_mm_override` changes the incoming-billet coefficient and upstream billet-saw loss, not that physical butt mass. The v0.18.0 correction can change calculated lengths, losses and discrete feasibility compared with earlier calculations, which used the incoming-billet section for the butt.

### Important process ranges

| Input | Supported range / rule |
|---|---|
| Cut length | 1000 to 15000 mm |
| Exit/profile speed | 1 to 100 m/min |
| Total trim per billet | Finite and nonnegative; geometry is checked after distribution across pulls |
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
    trim_total_per_billet_m=2,
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
