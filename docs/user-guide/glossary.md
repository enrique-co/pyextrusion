# Glossary of extrusion and PyExtrusion terms

This glossary is intended for readers who are new to aluminium extrusion or to the terminology used by PyExtrusion.

### Aluminium extrusion

A manufacturing process in which heated aluminium is forced through a die opening to create a long product with a constant cross-section.

### Bar

A finished cut length of extruded profile. In PyExtrusion, a request such as `PlanningRequest.bars(300)` means 300 finished cut lengths.

### Billet

A cylindrical piece of aluminium loaded into the extrusion press as raw material. PyExtrusion normally works with **whole billets**, not fractions of a billet.

### Billet diameter

The actual outside diameter of the billet before it is upset inside the container.

### Billet length

The length of billet required or used for a calculated process. PyExtrusion may report both a mathematical value and a recommended whole-millimetre value.

### Billet-on-billet / multi-billet continuous pull

A production situation in which material from successive billets contributes to one continuous extrusion pull. In PyExtrusion this is represented by the generic configuration `k_billets_1_profile`.

### Billets per pull

The number of billets contributing to one continuous pull. This can be 1 or more depending on the process and table geometry.

### Butt / butt discard

The short part of the billet intentionally left unextruded at the end of the stroke and discarded. It is sometimes called the butt end or discard.

### Complexity

A PyExtrusion process input used to represent a practical allowance for additional process losses. Public values are `normal`, `medium` and `high`.

### Container

The cylindrical press component that surrounds and supports the billet during direct extrusion.

### Container bore

The inside diameter of the container. Do not confuse it with the billet diameter: they are related but not identical.

### Cut

One finished-length division along the extruded pull. In PyExtrusion, `cuts` often means the number of requested-length pieces represented by one billet contribution.

### Cut length

The target finished bar length entered in millimetres. Example: a seven-metre bar is entered as `7000` mm.

### Dead time

A technical non-extruding time included in the current press-time model between relevant billet/process events. It is not the same as plant waiting time between production orders.

### Die

The tooling containing the opening(s) through which aluminium flows to create the profile cross-section.

### Direct extrusion

An extrusion process in which the ram pushes the billet through a stationary die in the same general direction as the ram movement. This is the process family currently modeled by PyExtrusion.

### Exit

One die opening producing one strand/profile at the same time. A die with two exits produces two simultaneous strands.

### Exit speed / extrusion speed

The linear speed of the extruded profile leaving the die, expressed by PyExtrusion in metres per minute.

### Extrusion ratio (RE)

A ratio describing the reduction from the incoming container cross-section to the total outgoing extrusion cross-section. It is an important process indicator, but it should not be used alone to accept or reject a production route.

### Fixed scrap

A PyExtrusion summary group containing fixed process losses such as butt, front scrap and saw-related losses.

### Front scrap / front crop

Length intentionally lost at the front/start of a pull or billet contribution before usable finished bars are considered.

### Good kg

Mass of finished product considered acceptable/output material, excluding the process-loss categories represented by the calculation.

### Gross productivity

Production rate before focusing only on good finished output. PyExtrusion distinguishes nominal and real gross productivity.

### Hollow profile

A profile containing one or more enclosed internal voids. Use `profile_type="hollow"`.

### Kerf

The width of material removed by a saw cut. PyExtrusion can model billet, puller and final-saw kerfs separately.

### Linear weight

Mass per unit length of one profile strand, normally expressed in kg/m. In PyExtrusion, `linear_weight_kg_m` is the linear weight of **one exit**.

### Net productivity

Good manufactured mass divided by the technical press time represented by the calculation. It is commonly expressed in kg/h.

### Nominal press size

The conventional inch size used to identify a press/billet class, such as 8-inch or 9-inch. In PyExtrusion the currently supported nominal range is 6 to 16 inches.

### PlanningCase

A PyExtrusion object combining a `Profile` and a `Process`. It describes a production method without specifying the required quantity.

### PlanningRequest

The quantity or capacity question applied to a `PlanningCase`, for example:

- 300 bars;
- 2500 kg;
- 1800 m;
- 20 billets;
- 2 hours available.

### Plate

A flat/solid profile family accepted with `profile_type="plate"`. PyExtrusion treats it within the solid family for calculation purposes.

### Press

The extrusion machine and its relevant limits/configuration as represented by the PyExtrusion `Press` object.

### Process / ProcessSpec

The PyExtrusion object describing how a profile is extruded: speed, cut length, front scrap, complexity and optional process overrides. It does not contain the order quantity.

### Production order

A user-defined order identifier plus a `PlanningCase` and a quantity-based `PlanningRequest`, represented by `ProductionOrder` in sequence calculations.

### Production sequence

An ordered list of production orders calculated one after another. PyExtrusion preserves the list order and accumulates technical press time only.

### Productivity index

An orientative PyExtrusion utilisation indicator combining several aspects of the calculated process. It is not a physical quantity and must not be used alone to choose a press.

### Profile

The extruded product cross-section. In PyExtrusion, a profile is mainly described by linear weight, number of exits, profile type and optionally an explicit section.

### Profiles per billet

The number of complete sequential profiles/pulls produced by one billet in the selected configuration. The current PyExtrusion model supports a maximum of two.

### Pull

A continuous length of extrusion handled on the press/runout table as one extrusion pull. One pull can contain the contribution of more than one billet.

### Puller

Equipment that grips/guides the extruded profile as it leaves the press and travels along the runout table.

### Puller saw

A saw operation associated with the puller/end of a pull. PyExtrusion can represent its kerf loss.

### Ram

The moving press component that applies force through the stem/dummy block to push the billet through the die.

### Ram speed

The forward speed of the press ram, commonly represented by PyExtrusion in mm/s. It is much lower than profile exit speed because the outgoing material cross-section is much smaller than the container cross-section.

### Recommended billet length

A practical billet-length suggestion returned by PyExtrusion, rounded upward to a whole millimetre from the mathematical calculated value.

### Runout table / table

The length available after the press for the extrusion pull. In PyExtrusion, `table_length_m` is mandatory because it strongly influences feasible pull geometry.

### Scrap / process loss

Material represented by the calculation as not becoming good finished product. PyExtrusion separates several loss categories so they can be inspected individually.

### Solid profile

A profile without an enclosed internal void. Use `profile_type="solid"`.

### Supported

A PyExtrusion status meaning the scenario is covered by the current approved calculation model. `supported=False` means the current model intentionally does not calculate that configuration.

### Table occupancy

The amount of runout-table length occupied by the calculated recommended pull configuration.

### Target productivity

A reference net productivity used for comparison/interpretation. A real plant target supplied by the user should be preferred when available.

### Theoretical start/end time

Clock timestamps obtained when a sequence is given a `start_at` value. They assume continuous technical press time and do not include unmodeled plant delays.

### Tubular profile

A tube-type profile accepted with `profile_type="tubular"`. PyExtrusion treats it within the hollow family for calculation purposes.

### Viable

A PyExtrusion status meaning a supported scenario has at least one process configuration that fits the current press/process constraints.

### Warning

A message drawing attention to an unusual, weak or potentially unfavorable calculated condition. Warnings support engineering review; they do not replace it.
