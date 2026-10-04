# Boundaries & Interpretation

## Model boundaries

PyExtrusion includes selected analytical engineering models, but it does not currently provide a complete model for:

- indirect extrusion;
- shaped-section, bridge-die or porthole-die final pressure/force prediction;
- full pressure evolution through the extrusion stroke;
- transient thermal evolution through billet, container, die and tooling;
- production-grade exit-temperature prediction;
- metallurgical-property prediction;
- die stress or die-life prediction;
- die correction;
- die caustic cleaning / soda treatment;
- die heating and preparation;
- die availability;
- billet stock and plant logistics;
- crews and operator availability;
- production shifts and calendars;
- maintenance or breakdowns;
- downstream bottlenecks;
- automatic order prioritisation;
- automatic work allocation between presses.

The Sheppard pressure/force calculation in `pyextrusion.engineering` is an
**equivalent-axisymmetric baseline**. A value below a configured press-force
limit is useful for mechanical feasibility screening, but it is not a validated
final force requirement for a real shaped or porthole die.

The difference \(F_{reserve}=F_{press}-F_{baseline}\) is also only a screening
indicator. It must not be presented as available hydraulic capacity, guaranteed remaining capacity, a safety
margin, force available for a porthole die or a prediction of the real die
load.

The thermal functions are likewise bounded: Stüwe is retained as a limited
analytical surface estimate, Saha functions expose local thermal source terms,
and Sheppard Eq. 2.25 gives an interface-temperature relation. None of these
functions is a production-grade exit-temperature predictor. PyExtrusion does
not reconstruct an Integral Profile or Saha's complete finite-difference field,
and it does not invent omitted boundary conditions.

---


## Engineering interpretation

PyExtrusion is intended to support engineering judgement, not replace it.

A technically responsible review should consider more than one result:

- supported and viable state;
- extrusion ratio;
- ram and extrusion speed;
- actual billet dimensions;
- billet length;
- table occupancy;
- number of exits;
- process losses;
- net productivity;
- warnings;
- known plant constraints not represented by the model.

A mathematically viable result can still be undesirable in the real plant because of alloy, die design, quality, temperature, surface, handling or operational constraints outside the software model.

---
