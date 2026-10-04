# Scope & Units

## Scope of the technical model

PyExtrusion currently models production calculations for **direct aluminium extrusion presses**.

The public model covers:

- press geometry;
- profile cross-sectional area;
- extrusion ratio;
- ram and extrusion speed relationship;
- billet geometry and billet mass;
- cut length and table occupancy;
- supported billet/pull configurations;
- process-loss categories;
- technical extrusion time;
- gross and net productivity;
- production planning by bars, kilograms, metres, billets or available press time;
- linear production sequences supplied by the user;
- comparison of the same case across multiple presses.

PyExtrusion also provides bounded analytical tools for constitutive behaviour,
equivalent-axisymmetric pressure/force and selected thermal relationships. They
are documented separately under [Engineering](../engineering/index.md).

PyExtrusion does not currently calculate a complete thermal, metallurgical or
die-specific extrusion-force model.

---


## Units and notation

PyExtrusion deliberately uses explicit engineering units.

| Quantity | Public unit |
|---|---|
| Nominal press size | in |
| Billet diameter | mm |
| Container bore diameter | mm |
| Billet length | mm of incoming billet |
| Physical butt thickness | mm inside the container |
| Equivalent butt length | mm of incoming billet representing the same butt mass |
| Cut length | mm |
| Table length | m |
| Canonical total trim / reject reserve | m of extrudate per exit per incoming billet (sum over its sequential pulls) |
| Trim per contribution | canonical total divided by sequential pulls per billet |
| Result trim_per_pull_m | m on one full pull, summed over its billet contributions |
| Legacy front scrap | m per contribution to one pull; p=2 uses it twice per billet |
| Exit / extrusion speed | m/min |
| Ram speed | mm/s or derived m/min |
| Linear weight | kg/m |
| Density | kg/m³ |
| Area | m² |
| Mass | kg |
| Productivity | kg/h or t/h |
| Dead time | s |
| Saw kerf | mm |
| Engineering pressure / flow stress | MPa |
| Engineering force baseline / reserve | MN |
| Mean strain rate | s⁻¹ |
| Temperature | °C |
| Local heat generation | W/m³ |
| Local heat flux | W/m² |

Important convention:

> A seven-metre cut length is entered as `7000 mm`, not `7`.

PyExtrusion uses strict numerical validation and does not silently convert numeric strings or guess a user's intended unit.

---
