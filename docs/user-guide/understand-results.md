# Understand the results

PyExtrusion returns many fields because different users need different views. You do not need to read every field for every calculation.

This chapter explains the main result families in practical terms.

### 1. Supported and viable

Read these first.

- **Supported**: the scenario is covered by the current PyExtrusion model.
- **Viable**: a supported configuration fits the selected press/process geometry.

A scenario can be supported but not viable.

### 2. Recommended configuration

This describes how billets and pulls are grouped by the calculation.

Common configurations include:

- `k_billets_1_profile`;
- `1_billet_2_profiles`.

See the [Glossary](glossary.md) if these terms are unfamiliar.

### 3. Extrusion ratio (RE)

The extrusion ratio indicates how strongly the incoming material cross-section is reduced into the total outgoing profile cross-section.

PyExtrusion reports an extrusion-ratio value and an informational status. Treat it as one engineering indicator among several, not as a standalone accept/reject rule.

### 4. Exit speed and ram speed

- **Exit speed**: speed of the extruded profile leaving the die.
- **Ram speed**: forward speed of the press ram/stem.

You can supply one of these as the process speed input. PyExtrusion resolves the other from the geometry.

### 5. Cuts and table occupancy

Important values include:

- theoretical cuts;
- cuts per billet;
- cuts per pull;
- table occupancy;
- table margin.

These help you understand how efficiently the calculated pull uses the available runout table.

### 6. Billet length

PyExtrusion can expose:

- calculated billet length;
- recommended billet length rounded upward to a whole millimetre;
- minimum and maximum billet margins.

The automatic calculation is designed around a billet-first principle: it prefers the longest valid billet for the process rather than shortening a valid billet only to increase the number of billets in one pull.

### 7. Bars, billets and pulls

Do not confuse these quantities:

- **bar**: finished cut length requested/produced;
- **billet**: cylindrical input material loaded into the press;
- **pull**: continuous extrusion length handled as one pull on the runout table.

One pull can contain material from more than one billet in a multi-billet continuous configuration.

### 8. Scrap / process losses

PyExtrusion reports individual and grouped losses, including categories such as:

- butt;
- front scrap;
- billet saw;
- puller saw;
- final saw;
- startup allowance;
- complexity allowance.

Two useful summary values are:

- **fixed scrap**: fixed process-loss group;
- **total scrap**: broader estimated loss group including startup and complexity allowances.

These are engineering estimates. Plant measurements remain the best reference when available.

### 9. Productivity

Useful productivity outputs include:

- nominal gross kg/h;
- real gross kg/h;
- real net kg/h;
- target/reference net kg/h when available.

For most practical production comparisons, **real net kg/h** is one of the most useful values because it relates good manufactured mass to the technical press time represented by the model.

### 10. Productivity index

PyExtrusion can report an orientative productivity/utilisation index.

Important:

> The productivity index is not a physical quantity and must not be used alone to make the final industrial decision.

Always read it together with:

- actual net productivity;
- losses;
- billet use;
- table use;
- configuration;
- extrusion ratio;
- warnings;
- plant constraints that PyExtrusion does not model.

### 11. Timing

The current technical press time includes the extrusion time and the technical dead time modeled by PyExtrusion.

It does not automatically include external delays between production orders.

### 12. Warnings

Warnings are there to draw attention to potentially weak or unusual process outcomes. They are not a substitute for engineering judgement.

When a case is completely non-viable or unsupported, focus first on the main reason instead of secondary indicators.

---
