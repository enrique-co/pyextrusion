# Boundaries & Interpretation

## Model boundaries

PyExtrusion does not currently provide a complete model for:

- indirect extrusion;
- full extrusion pressure / required press-force prediction;
- thermal evolution;
- exit-temperature prediction;
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

The presence of a press-force field does not currently mean that PyExtrusion validates the extrusion force required by a profile.

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
