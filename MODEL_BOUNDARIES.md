# Model boundaries

Understanding what a tool does **not** calculate is as important as understanding what it does.

### Current process scope

PyExtrusion 0.17.0.dev0 is intended for **direct aluminium extrusion**.

### Current supported production geometry

The current model supports:

- one or more billets contributing to one continuous pull, when permitted by process/table geometry;
- one billet producing one complete pull;
- one billet producing two complete sequential pulls.

A scenario requiring three or more complete sequential profiles/pulls from one billet is outside the current supported model.

### Not currently modeled

PyExtrusion includes selected analytical estimates for AA6063 direct extrusion:

- equivalent axisymmetric geometry;
- modified Feltham mean strain rate;
- Zener-Hollomon / Sheppard-Wright flow stress;
- Sheppard axisymmetric pressure, container friction, breakthrough pressure and required force;
- Stuwe three-component surface exit-temperature estimate;
- Saha local thermal source terms for deformation, billet-container friction, dead-metal-zone friction and die-bearing friction;
- Sheppard Eq. 2.25 billet/container interface-temperature relation using source-stated aluminium and Cr-V tooling-steel thermal properties.

These estimates are scoped to a single operation point and keep their units,
source traceability and limitations explicit.

PyExtrusion does not currently provide a complete model for:

- indirect extrusion;
- shaped-section, porthole-die or bridge-die pressure corrections;
- Integral Profile thermal reconstruction;
- transient thermal evolution through billet, container, die and tooling;
- reconstruction of Saha's complete finite-difference temperature field and its omitted boundary conditions;
- conversion of Saha local heat-source terms into an exit-temperature prediction without an explicit transient heat-balance model;
- source-exact partition of newly generated friction heat between aluminium and tooling; Eq. 2.25 predicts interface temperature from the two body temperatures and properties but does not itself define friction-heat partition;
- metallurgical quality prediction;
- die stress or die-life prediction;
- die availability;
- die caustic cleaning / soda treatment;
- die correction loops;
- die heating;
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
