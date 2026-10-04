# Materials & Rheology

## Constitutive models

PyExtrusion 0.19.0 exposes two separate hot-working constitutive datasets:

- `AA6063`;
- `AA6060`.

Use the short public names in normal workflows:

```python
from pyextrusion.engineering import AA6060, AA6063
```

These names are aliases of the existing model objects, not copies or new datasets. The source-specific names remain available for backward compatibility; see the [provenance mapping](../technical-reference/references.md#public-alloy-aliases-and-provenance). No material registry or additional alloy dataset is introduced.

Both are `HotWorkingConstitutiveModel` instances. They contain the parameters
used by the hyperbolic-sine flow-stress relationship together with source
references and explicit notes. The two alloys are not interchangeable, and the
constants do not claim to represent every chemistry, homogenisation state,
supplier or production lot.

## Equivalent geometry

`equivalent_extrudate_diameter_mm()` derives a circular diameter that preserves
the total simultaneously extruded area for a supplied container diameter and
extrusion ratio. It is an **equivalent-axisymmetric geometry**, not a claim that
the real profile is circular.

## Modified Feltham mean strain rate

`modified_feltham_mean_strain_rate_s_1()` evaluates the scalar mean strain-rate
relationship used by the Sheppard model. If the deformation semi-angle is not
provided, PyExtrusion evaluates the documented empirical relationship from the
extrusion ratio.

The result is a mean value for the deformation zone. It is not a local
strain-rate field.

## Zener-Hollomon and flow stress

The public rheology chain is:

1. calculate mean strain rate;
2. calculate `log_zener_hollomon_parameter()` or
   `zener_hollomon_parameter_s_1()`;
3. calculate `steady_state_flow_stress_mpa()` from `Z`, or use
   `flow_stress_mpa()` for the combined calculation.

The logarithmic API is useful when `Z` would be inconveniently large. All
temperatures passed to the public API are in degrees Celsius; conversion to
absolute temperature is performed internally.

See the [Engineering API](../api-reference/engineering.md) for an executable
example and the [technical references](../technical-reference/references.md)
for source attribution.
