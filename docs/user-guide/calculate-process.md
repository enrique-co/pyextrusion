# Calculate a process

Use `calculate_process()` when you want to understand **how a profile fits a press** before specifying a production quantity.

```python
from pyextrusion import calculate_process

result = calculate_process(press, case)
```

### Typical questions answered

A process calculation can tell you:

- whether the scenario is supported by the current model;
- whether the supported process is geometrically viable;
- recommended configuration;
- cuts per billet;
- billet length;
- recommended whole-millimetre billet length;
- bars per billet;
- billets per pull;
- bars per pull;
- table occupancy;
- extrusion ratio;
- resolved exit speed;
- ram speed;
- extrusion time per billet;
- warnings.

Example:

```python
print(result.supported)
print(result.viable)
print(result.recommended_configuration)
print(result.cuts)
print(result.recommended_billet_length_mm)
print(result.bars_per_billet)
print(result.billets_per_pull)
print(result.extrusion_ratio)
print(result.ram_speed_mm_s)
```

### Supported versus viable

These are different ideas.

#### Supported

`result.supported` tells you whether the requested situation is covered by the current PyExtrusion model.

Example of an unsupported situation: a geometry that would require more than two complete sequential profiles from one billet.

#### Viable

`result.viable` tells you whether a **supported** configuration can actually fit the press/process geometry.

A useful reading order is therefore:

```python
if not result.supported:
    print(result.unsupported_reason)
elif not result.viable:
    print(result.warnings)
else:
    print("Supported and viable")
```

### Configuration names

You may see names such as:

#### `k_billets_1_profile`

One continuous pull is formed from one or more billets. The number of billets per pull is calculated from the process and table geometry.

#### `1_billet_2_profiles`

One billet produces two complete sequential pulls/profiles.

PyExtrusion currently supports a maximum of two sequential profiles from one billet.

### Billet recommendation

PyExtrusion can return both:

- the mathematical calculated billet length;
- a recommended billet length rounded upward to a whole millimetre.

The rounded value is intended as a practical manufacturing suggestion. If your plant uses a specific real billet length, use that real value when appropriate in your workflow.

---
