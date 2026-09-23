# Formula Summary

## Quick formula summary

### Profile area

\[
A_1 = \frac{w}{\rho}
\]

\[
A_{total} = A_1 n
\]

### Container area

\[
A_c = \frac{\pi D_c^2}{4}
\]

### Extrusion ratio

\[
RE = \frac{A_c}{A_{total}}
\]

### Volume constancy

\[
V_r A_c = V_e A_{total}
\]

### Ram speed from exit speed

\[
V_r = V_e \frac{A_{total}}{A_c}
\]

### Billet area

\[
A_b = \frac{\pi D_b^2}{4}
\]

### Billet mass per millimetre

\[
m_{b,mm} = \frac{A_b \rho}{1000}
\]

### Nominal gross productivity

\[
Q_{gross,nominal}
=
w_{total}V_e60
\]

### Technical extrusion time

\[
T_{extrusion}
=
\frac{L_{extruded}}{V_e}
\]

### Net productivity

\[
Q_{net,real}
=
\frac{M_{good,manufactured}}{T_{technical,h}}
\]

---

## AA6063 direct-extrusion analytical estimates

For a single AA6063 direct-extrusion operation point, PyExtrusion composes the
following validated analytical pieces without adding porthole, bridge-die or
Integral Profile corrections.

### Equivalent extrudate diameter

\[
D_E = \frac{D_C}{\sqrt{R}}
\]

### Modified Feltham mean strain rate

\[
\dot{\bar\varepsilon}
=
\frac{
6 V_R D_C^2 (0.171 + 1.86 \ln R)\tan\alpha
}{
D_C^3 - D_E^3
}
\]

with:

\[
\alpha = 38.7 + 6.9 \ln R
\]

### Zener-Hollomon and Sheppard-Wright flow stress

\[
\ln Z = \ln \dot{\bar\varepsilon} + \frac{Q}{RT}
\]

\[
Z = A[\sinh(\alpha_s \sigma)]^n
\]

For the built-in AA6063 model:

\[
\alpha_s=0.040\;MPa^{-1},\quad n=5.385,\quad Q=141550\;J/mol,\quad \ln A=22.5
\]

### Axisymmetric pressure and force

\[
p_{steady}
=
\bar\sigma (0.171 + 1.86 \ln R)
+
\bar\sigma\frac{4mL_B}{\sqrt{3}D_C}
\]

\[
\Delta p_{breakthrough}
=
6.62 + \frac{0.921\ln(Z/A)}{\alpha_s n}
\]

\[
F = p_{peak} A_C
\]

### Stuwe surface exit-temperature estimate

\[
T_{exit,surface}
=
T_B + \Delta T_1 + \Delta T_2 + \Delta T_3
\]

\[
\Delta T_1=
\frac{\bar\sigma\ln R}
{\sqrt3\,\rho C_p}
\]

\[
\Delta T_2=
\frac{\bar\sigma}
{4\sqrt3\,\rho C_p}
\sqrt{\frac{V_RL_B}{a}}
\]

\[
\Delta T_3=
\frac{\bar\sigma}
{4\sqrt3\,\rho C_p}
\sqrt{\frac{V_EL_D}{a}},
\qquad
a=\frac{k}{\rho C_p}
\]

This is a surface estimate, not a complete transient thermal field.
