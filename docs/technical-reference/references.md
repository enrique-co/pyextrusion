# Technical Basis & References

## Technical basis and references

The fundamental physical relationships documented publicly by PyExtrusion are standard aluminium-extrusion relationships.

A principal technical reference used during development is:

**P. K. Saha, _Aluminum Extrusion Technology_.**

Additional analytical models implemented in the engineering package are traced
to:

**T. Sheppard, _Extrusion of Aluminium Alloys_ (1999).**

PyExtrusion uses Sheppard's AA6063 hot-working constants, modified Feltham
strain-rate context, axisymmetric pressure correlations, the Stuwe
surface-temperature approximation reproduced by Sheppard, and the Eq. 2.25
billet/tooling interface-temperature relation.

For AA6060, PyExtrusion keeps a separate source-traced constitutive dataset
attributed to **Verlinden, Suhadi and Delaey (1993)** and cross-checked against
later extrusion literature. The AA6060 and AA6063 parameter sets are not treated
as interchangeable.

From Saha, PyExtrusion exposes selected local thermal source terms for
deformation and frictional interfaces. Those terms are not promoted to a full
finite-difference temperature solver because the complete boundary-condition
set required for such a reconstruction is not contained in the implemented
source material.

Relevant topics include:

- conventional direct extrusion;
- billet-on-billet extrusion and continuous lengths;
- extrusion ratio based on container-bore area and total extrusion area;
- volume constancy;
- relationship between ram speed and extrusion speed;
- principal extrusion variables;
- productivity and billet-length considerations.

The literature also makes clear that extrusion behaviour depends on a broader set of variables — including alloy, temperature, friction, extrusion ratio, billet length, die design and speed — than those currently represented by the PyExtrusion production model.

PyExtrusion-specific defaults, supported software ranges and composite interpretation indicators are engineering choices of the project and should not be presented as universal industry laws.

---


## Relationship to the User Guide

Use the **PyExtrusion User Guide** when you want to learn how to:

- install the package;
- create a press;
- create a profile and process;
- plan an order;
- calculate a production sequence;
- compare presses;
- use JSON or the CLI;
- interpret errors;
- learn extrusion terminology.

Use this **Technical Reference** when you want to understand the public engineering meaning of the calculations.

Internal model-governance and implementation specifications are not part of the public documentation.

---
