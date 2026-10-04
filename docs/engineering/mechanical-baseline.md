# Mechanical Baseline

## Pressure components

`axisymmetric_pressure_breakdown()` keeps the following components explicit:

- steady deformation pressure;
- billet-container friction increment;
- breakthrough increment;
- peak pressure;
- force obtained from peak pressure and container-bore area.

The billet contact length and friction factor are caller-supplied model inputs.
PyExtrusion does not infer either value from a profile name or die type.

When obtaining the initial billet length from production calculations, pass the corrected full-precision `billet_length_mm` to `upset_billet_length_mm()`. The existing geometric relation `L_upset = L_billet * (D_B / D_C)**2` is unchanged. Do not add another butt or apply another area-ratio conversion in the pressure chain. See [physical butt and coefficient semantics](../technical-reference/geometry.md#physical-butt-and-equivalent-incoming-billet-length), including the measured-coefficient limitation.

## Force naming

The force returned by `pressure.required_force_mn` must be interpreted as:

\[
F_{baseline}=p_{peak}A_C
\]

`F_baseline` is an **equivalent-axisymmetric mechanical screening baseline**. The Python
attribute retains the public name `required_force_mn`, but that name does not
make the value a final prediction for a real shaped, bridge or porthole die.

It does not include a shaped-section correction, bridge/porthole pressure
correction, die-specific calibration, transient stroke reconstruction or
tooling-response model.

## Press comparison

When a configured scalar press limit is compared with the baseline, the
arithmetic difference may be written as:

\[
F_{reserve}=F_{press}-F_{baseline}
\]

`check_force_capacity()` and `check_press_force_capacity()` expose this
difference as `margin_mn`, together with utilization and `within_limit`.
Public interpretation should call the difference **reserve**, not safety
margin.

`F_reserve` is only a screening indicator. It is not:

- available hydraulic capacity or a certified hydraulic reserve;
- guaranteed remaining press capacity;
- a safety margin or safety factor;
- force available for a porthole die;
- a prediction of the real die load.

A positive reserve means only that the equivalent-axisymmetric baseline is
below the configured scalar used in that comparison.
