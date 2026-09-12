# Losses & Productivity

## Billet recommendation

PyExtrusion calculates the billet length required by the selected supported process geometry and press constraints.

The public output can distinguish between:

- a calculated billet length with full numerical precision;
- a practical recommended billet length rounded to a whole millimetre.

The recommended whole-millimetre value is intended as an engineering convenience. Users should still apply plant-specific billet-cutting tolerances and operating practice.

Finished cut length is interpreted as the **net finished-bar length**. Physical downstream saw kerfs therefore require additional extruded metal beyond the finished bars. Puller and final-saw kerf allowances are included in the physical process length used for billet geometry, table occupancy and technical extrusion time.

For multi-billet continuous pulls, pull-level kerfs are shared by the billets forming the pull. The process-level billet recommendation represents the selected complete-pull geometry. If an order finishes with a partial multi-billet pull, exact order-level saw events are used for timing and losses; the final partial pull can require plant-specific billet-length handling.

The exact internal decision logic used to select among valid candidates is implementation detail and is not part of the public Technical Reference.

---

## Process-loss model

PyExtrusion separates process losses into understandable engineering categories.

### Fixed process losses

The fixed-loss group can include:

- butt / discard;
- front scrap;
- billet saw kerf;
- puller saw kerf;
- final saw kerf.

The public fixed-loss total is:

\[
M_{fixed} =
M_{butt}
+ M_{front}
+ M_{billet\ saw}
+ M_{puller}
+ M_{final\ saw}
\]

and its percentage relative to manufactured good output is:

\[
Scrap_{fixed,\%}
=
\frac{M_{fixed}}{M_{good,manufactured}}
\times 100
\]

### Additional modeled allowances

PyExtrusion can also represent additional planning allowances such as:

- startup allowance;
- process-complexity allowance.

The total modeled scrap is therefore:

\[
M_{total\ scrap}
=
M_{fixed}
+ M_{startup}
+ M_{complexity}
\]

and:

\[
Scrap_{total,\%}
=
\frac{M_{total\ scrap}}
{M_{good,manufactured}}
\times 100
\]

Startup and complexity are **modeled planning allowances**, not additional physical length inserted into the billet and not additional extrusion time. They should therefore not be interpreted as an exact physical mass balance or as measured plant scrap unless a user has deliberately calibrated the corresponding assumptions to plant data.

These categories are calculation aids. They are not a universal scrap standard for every extrusion plant.

---

## Saw kerf convention

A saw kerf represents the physical thickness of material lost by a cutting operation.

PyExtrusion distinguishes billet, puller and final saw kerfs because they occur at different process boundaries:

- **billet saw kerf** is an upstream billet-stock loss and does not add extrusion length;
- **puller saw kerf** is downstream extruded metal and is reserved in the physical extruded length;
- **final saw kerf** is downstream extruded metal and is reserved in the physical extruded length for the represented cut events.

Accordingly, puller and final-saw kerfs contribute to billet material requirement, table occupancy where applicable, and technical extrusion time.

A configured kerf of:

`0 mm`

means:

> that operation contributes no material loss through saw thickness.

It does not automatically remove unrelated cycle time or other process effects.

---

## Good output

For a finished bar:

\[
M_{bar} = L_{cut} \times w
\]

where:

- \(L_{cut}\) = **net finished bar length**, m;
- \(w\) = linear weight of one finished profile, kg/m.

For a production quantity of \(N\) finished bars:

\[
M_{good} = N \times L_{cut} \times w
\]

Saw kerf is additional material loss and does not reduce the declared finished-bar length.

The number of exits affects how many bars are produced simultaneously, but the mass of one finished bar is still based on the linear weight of one profile.

---

## Nominal gross productivity

The nominal extrusion mass flow is based on total linear weight leaving the die and extrusion speed.

If:

\[
w_{total} = w \times n_{exits}
\]

then:

\[
Q_{gross,nominal}
=
w_{total} \times V_e \times 60
\]

where:

- \(Q_{gross,nominal}\) = kg/h;
- \(w_{total}\) = kg/m across all exits;
- \(V_e\) = m/min.

This is an idealised extrusion-rate quantity and does not by itself represent finished good kg/h.

---

## Technical extrusion time

The fundamental extrusion-time relationship is:

\[
T_{extrusion}
=
\frac{L_{extruded,physical}}{V_e}
\]

where the physical extruded length includes finished product, represented front scrap, and downstream puller/final-saw kerf allowances.

When expressed in metres and metres per minute, the result is in minutes.

PyExtrusion then adds the technical dead-time events represented by the current process model:

\[
T_{technical}
=
T_{extrusion}
+
T_{dead}
\]

This is **technical press time**, not complete plant elapsed time.

It excludes unmodeled waits such as die availability, die correction, caustic cleaning, shift changes, maintenance or material logistics. Startup and complexity allowances also do not add time unless a future or external model explicitly represents such time.

---

## Real gross and net productivity

PyExtrusion distinguishes between gross and net production performance.

### Real gross productivity

Real gross productivity relates the physically represented extruded material to the calculated technical time.

Conceptually:

\[
Q_{gross,real}
=
\frac{M_{extruded,physical}}
{T_{technical,h}}
\]

The physically represented extruded mass includes good product, front scrap and downstream saw kerfs. Modeled startup and complexity allowances remain outside this physical extrusion boundary.

### Net productivity

Net productivity uses good manufactured output:

\[
Q_{net,real}
=
\frac{M_{good,manufactured}}
{T_{technical,h}}
\]

Net kg/h is one of the most useful results when comparing the practical production performance of the same profile on different presses, provided the same time boundary and process assumptions are used.

---

## Productivity and geometric indices

PyExtrusion can expose composite indices intended to help interpret how favourably a case uses the represented press and process.

These indices are **not physical laws** and should never replace the underlying engineering results.

The public interpretation should focus on the factors they summarize, including:

- net productivity;
- relation to an applicable productivity reference;
- process losses;
- cut utilisation;
- table utilisation;
- billet utilisation.

The exact internal weighting and scoring rules are intentionally not part of the public Technical Reference.

When comparing presses, users should inspect the actual physical outputs — kg/h, billet length, RE, losses, table use and warnings — rather than choosing a press only from one composite score.

---
