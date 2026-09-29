# Thermal Boundaries

PyExtrusion 0.18.0 exposes three distinct thermal tool families. They must not
be combined into a claim that the package predicts production exit
temperature.

## Stüwe analytical estimate

The Python API uses the ASCII spelling `stuwe_*`. The Stüwe model implemented
by `stuwe_surface_exit_temperature_estimate()` is a limited three-component
analytical surface-temperature estimate reproduced by Sheppard.

It is not a transient temperature field and does not explicitly represent all
container, die, tooling, porthole or temperature-dependent material effects.

## Saha local source terms

The `saha_*` functions expose local heat-generation or heat-flux source terms
for:

- deformation;
- billet-container friction;
- dead-metal-zone friction;
- die-bearing friction.

These functions do not integrate a temperature field. A transient heat balance,
geometry, heat partition and complete boundary conditions would still be
required to calculate temperatures.

## Sheppard Eq. 2.25

`sheppard_billet_container_interface_temperature_c()` evaluates the stated
billet/tooling interface-temperature relationship using the supplied body
temperatures and thermal properties. It does not define how newly generated
friction heat is partitioned between aluminium and tooling.

## Explicitly outside the model

PyExtrusion does not currently:

- provide a production-grade exit-temperature predictor;
- reconstruct an Integral Profile temperature field;
- reconstruct Saha's complete finite-difference solution;
- invent missing boundary conditions;
- infer source-exact friction-heat partition;
- model complete transient heat storage in billet, container, die or tooling.

See the [Engineering API](../api-reference/engineering.md) for runnable calls
that keep these three result types separate.
