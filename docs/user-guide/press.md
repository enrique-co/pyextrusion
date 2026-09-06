# Define a press

A `Press` represents one **direct extrusion press** and its relevant physical/operational limits.

### Minimum information

The simplest practical definition is:

```python
from pyextrusion import Press

press = Press(
    name="Example 8-inch press",
    nominal_size_in=8,
    table_length_m=54,
)
```

`table_length_m` is mandatory. PyExtrusion does not infer table length from nominal press size because two presses with the same nominal size may have very different runout tables.

### Use real plant values whenever possible

```python
press = Press(
    name="Production line",
    nominal_size_in=9,
    billet_diameter_mm=228,
    container_diameter_mm=236,
    billet_min_length_mm=500,
    billet_max_length_mm=1300,
    table_length_m=64,
    dead_time_sec=14,
    target_net_productivity_kg_h=2250,
    press_force_t=3500,
)
```

If you supply real plant dimensions, they take priority over PyExtrusion defaults.

### Important public input ranges

| Input | Supported range / rule |
|---|---|
| Nominal press size | 6 to 16 inches, whole integer |
| Billet minimum length | 100 to 3000 mm |
| Billet maximum length | 100 to 3000 mm |
| Table length | 10 to 100 m |
| Technical dead time | 5 to 30 s |
| Saw kerf | 0 mm, or 3 to 10 mm |

The billet minimum must not be greater than the billet maximum.

### Saw kerfs

The three saw-related values are independent:

- billet saw;
- puller saw;
- final saw.

A value of `0` is allowed and means that the corresponding operation contributes no material loss from kerf.

Example:

```python
from pyextrusion import Press, SawSpec

press = Press(
    name="Press with billet shear",
    nominal_size_in=8,
    table_length_m=54,
    saws=SawSpec(
        billet_mm=0,
        puller_mm=5,
        final_mm=5,
    ),
)
```

### Defaults versus real values

PyExtrusion can infer several practical defaults from nominal press size when real values are unavailable. These defaults are intended to make preliminary calculations possible; they are **not universal press-design laws**.

For engineering or production use, prefer measured/known plant values whenever they are available.

---
