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

PyExtrusion does not currently calculate a complete thermal, metallurgical or force-based extrusion model.

---


## Units and notation

PyExtrusion deliberately uses explicit engineering units.

| Quantity | Public unit |
|---|---|
| Nominal press size | in |
| Billet diameter | mm |
| Container bore diameter | mm |
| Billet length | mm |
| Cut length | mm |
| Table length | m |
| Front scrap | m |
| Exit / extrusion speed | m/min |
| Ram speed | mm/s or derived m/min |
| Linear weight | kg/m |
| Density | kg/m³ |
| Area | m² |
| Mass | kg |
| Productivity | kg/h or t/h |
| Dead time | s |
| Saw kerf | mm |

Important convention:

> A seven-metre cut length is entered as `7000 mm`, not `7`.

PyExtrusion uses strict numerical validation and does not silently convert numeric strings or guess a user's intended unit.

---
