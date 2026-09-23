# Model boundaries

Understanding what a tool does **not** calculate is as important as understanding what it does.

### Current process scope

PyExtrusion 0.17 development is intended for **direct aluminium extrusion**.

### Current supported production geometry

The current production model supports:

- one or more billets contributing to one continuous pull, when permitted by process/table geometry;
- one billet producing one complete pull;
- one billet producing two complete sequential pulls.

A scenario requiring three or more complete sequential profiles/pulls from one billet is outside the current supported production model.

### Advanced engineering layer

pyextrusion.engineering now also provides source-traced physical models and identities that are deliberately kept separate from the production/planning engine.

The current advanced engineering layer includes:

- equivalent circular extrusion geometry and mean extrusion strain-rate helpers;
- Zener-Hollomon and Sheppard-Wright steady-state hot-flow-stress calculations;
- named constitutive data for AA6063 from Sheppard and an additional traced AA6060 literature model;
- axisymmetric/equivalent direct-extrusion pressure using Sheppard steady-pressure, billet/container-friction and breakthrough correlations;
- conversion of predicted specific pressure to required axial force and comparison with an explicitly configured press-force limit;
- the three-component Stuwe analytical temperature-rise approximation reproduced by Sheppard, including deformation, billet/container surface-layer and die-land surface heating;
- a deliberately labelled **surface exit-temperature estimate** based on that Stuwe approximation.

These engineering models are not silently coupled into the existing production/planning calculations.

### Important physical boundaries

The current pressure model is an **axisymmetric/equivalent-section direct-extrusion model**.

It does not yet provide a complete geometry correction for:

- porthole or bridge dies;
- weld chambers;
- multi-stage hollow-section flow;
- arbitrary shaped-section redundant work or bearing distribution.

A hollow or tubular profile must therefore not be presented as having a fully predicted real die load solely from the current axisymmetric pressure result.

The current thermal model is the **Stuwe three-component analytical approximation as reproduced by Sheppard**.

It does not yet provide:

- the full Sheppard-Wood Integral Profile transient solution;
- explicit die-temperature or container-temperature conduction terms;
- ram/dummy-block transient heat storage;
- temperature-dependent thermal-property functions;
- a full through-thickness temperature field;
- complete stroke-wise thermal evolution;
- porthole/bridge-die thermal corrections.

Its reported exit-temperature quantity must therefore remain labelled as an analytical **surface estimate**, not as a complete transient thermal solution.

### Not currently modeled

PyExtrusion does not currently provide a complete model for:

- indirect extrusion;
- metallurgical quality prediction;
- die stress or die-life prediction;
- complete porthole/bridge-die pressure prediction;
- full transient thermal evolution;
- die availability;
- die caustic cleaning / soda treatment;
- die correction loops;
- die heating logistics;
- billet stock and logistics;
- operator or crew availability;
- plant shifts and calendars;
- weekends and breaks;
- maintenance;
- breakdowns;
- downstream bottlenecks;
- automatic production-order prioritisation;
- automatic production-order reordering;
- multi-press work allocation;
- automatic selection of a "best" press.

### Sequence timing boundary

A production sequence is a mathematical accumulation of the technical press time calculated for each supplied order.

The end of one calculated order is the start of the next one in the returned sequence unless an external application adds other constraints.

This is useful for comparing pure press-time requirements, but it should not be presented as a guaranteed plant completion time.

### Engineering judgement remains necessary

PyExtrusion is an engineering calculation aid. It does not replace:

- plant experience;
- process trials;
- tooling knowledge;
- quality requirements;
- safety procedures;
- equipment limits not represented in the model.

---
