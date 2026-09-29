# Engineering

`pyextrusion.engineering` provides source-traced analytical building blocks for
selected direct-extrusion calculations. The functions are deterministic,
unit-explicit and independent from plant-specific assumptions unless those
assumptions are supplied by the caller.

## Public model groups

- [Materials & rheology](materials-rheology.md): AA6063 and AA6060
  constitutive datasets, equivalent geometry, modified Feltham mean strain
  rate, Zener-Hollomon and steady-state flow stress.
- [Mechanical baseline](mechanical-baseline.md): Sheppard axisymmetric
  deformation pressure, billet-container friction, breakthrough pressure and
  the equivalent-axisymmetric force baseline.
- [Thermal boundaries](thermal-boundaries.md): the limited Stüwe analytical
  estimate, Saha local thermal source terms and Sheppard Eq. 2.25 interface
  temperature.
- [Engineering API](../api-reference/engineering.md): runnable examples using
  the public 0.18.0 interface.

## Interpretation boundary

These functions evaluate individual analytical relationships or a bounded
single-operation composition. They do not turn a shaped profile into an
axisymmetric die, infer missing press data or calibrate a plant-specific model.

In particular, PyExtrusion does not add hidden corrections for shaped sections,
bridge dies or porthole dies. Engineering results must be reviewed together
with tooling knowledge, equipment limits and process experience.
