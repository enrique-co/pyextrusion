# Geometry & Speeds

## Direct extrusion and the container reference area

In direct extrusion, the billet is placed inside the container and pushed through the die by the ram.

For the public geometric model, two circular areas must be kept distinct:

1. **container bore area**;
2. **actual billet area**.

They are not interchangeable.

### Container bore area

For an internal container diameter \(D_c\):

\[
A_c = \frac{\pi D_c^2}{4}
\]

with \(D_c\) converted to metres when \(A_c\) is required in m².

PyExtrusion uses the **container bore area** for:

- extrusion ratio;
- ram/extrusion speed relationship.

### Actual billet area

For actual billet diameter \(D_b\):

\[
A_b = \frac{\pi D_b^2}{4}
\]

The actual billet area is used for billet material mass and billet-length calculations.

This distinction is important because the billet diameter is normally smaller than the container bore diameter.

---


## Profile area from linear weight

When the geometrical cross-sectional area of one exit is not supplied directly, PyExtrusion can derive it from linear weight and density.

For one exit:

\[
A_1 = \frac{w}{\rho}
\]

where:

- \(A_1\) = cross-sectional area of one exit, m²;
- \(w\) = linear weight of one exit, kg/m;
- \(\rho\) = material density, kg/m³.

For a die with \(n\) simultaneous exits:

\[
A_{total} = A_1 \times n
\]

The total outgoing cross-section therefore already includes the number of exits.

---


## Extrusion ratio

The extrusion ratio, RE, is calculated using the container bore area and the **total outgoing extrusion area**:

\[
RE = \frac{A_c}{A_{total}}
\]

For a multi-exit die, \(A_{total}\) includes all exits.

This follows the standard volume/area definition used in aluminium extrusion engineering.

### Interpretation

RE is an important process indicator because it represents the reduction in cross-sectional area through the die.

PyExtrusion may classify the calculated value as low, normal/OK or high according to the profile family represented by the current model.

RE should be treated as an **engineering indicator**, not as a standalone accept/reject criterion. Real extrudability also depends on alloy, geometry, die design, temperature, speed, friction, press capability and other factors not completely modeled by PyExtrusion.

---


## Ram speed and extrusion speed

PyExtrusion uses conservation of volume between material moving inside the container and the total material leaving the die:

\[
V_r A_c = V_e A_{total}
\]

where:

- \(V_r\) = ram speed;
- \(V_e\) = extrusion/exit speed;
- \(A_c\) = container bore area;
- \(A_{total}\) = total extrusion area.

Therefore:

\[
V_r = V_e \frac{A_{total}}{A_c}
\]

and, conversely:

\[
V_e = V_r \frac{A_c}{A_{total}}
\]

Because:

\[
RE = \frac{A_c}{A_{total}}
\]

the relationship can also be written as:

\[
V_e = V_r \times RE
\]

### Public input behaviour

A user may define either:

- exit speed; or
- ram speed.

They are alternative inputs for a new calculation. Supplying both as independent inputs would create an ambiguous case, so PyExtrusion expects one governing speed and derives the other.

---


## Billet mass

Using the actual billet area:

\[
A_b = \frac{\pi D_b^2}{4}
\]

the mass of aluminium per millimetre of billet can be represented as:

\[
m_{b,mm} = \frac{A_b \rho}{1000}
\]

where:

- \(A_b\) is in m²;
- \(\rho\) is in kg/m³;
- \(m_{b,mm}\) is in kg/mm.

This coefficient links material mass to billet length.

If a plant has a measured or controlled billet mass coefficient, PyExtrusion can use a plant-specific value instead of relying solely on theoretical geometry.

---


## Cut length, table and pulls

The finished cut length is converted from millimetres to metres:

\[
L_{cut,m} = \frac{L_{cut,mm}}{1000}
\]

The runout/table length limits the length that can physically be represented in one pull.

A useful simple geometric reference is the number of whole finished lengths that could fit along the table before other process allowances are considered:

\[
n_{theoretical} = \left\lfloor\frac{L_{table}}{L_{cut}}\right\rfloor
\]

The actual calculated production arrangement may be lower because it must also respect billet limits, front scrap and the supported production geometry.

### Pull

A **pull** is the continuous extrusion length handled as one production length on the runout table before final division.

Several billets may contribute to one continuous pull when the process geometry allows it.

---


## Supported production geometry

PyExtrusion currently supports two public production families.

### One or more billets contributing to one continuous pull

This is represented by the generic configuration:

`k_billets_1_profile`

where `k` is the number of billets contributing to that continuous pull.

The number is determined from the valid process and available table geometry rather than being limited to a fixed value such as two or three.

### One billet producing two sequential complete pulls

PyExtrusion also supports:

`1_billet_2_profiles`

This represents one billet producing two complete extrusion pulls sequentially.

### Current support boundary

A configuration requiring three or more complete sequential pulls from one billet is outside the currently supported model.

`supported=False` means that PyExtrusion is not approved to calculate that configuration. It does **not** mean that the process is physically impossible in every extrusion plant.

---
