# User Guide

Use this guide to learn PyExtrusion from a practical, task-oriented point of view.

## What PyExtrusion can do

PyExtrusion can help you:

- describe a direct extrusion press;
- describe a profile and its extrusion conditions;
- evaluate whether a supported process is geometrically viable;
- calculate billet-related results, extrusion ratio, speeds, cuts and pull grouping;
- estimate process losses and technical press time;
- estimate real gross and net productivity;
- plan one production order in bars, kilograms, metres or billets;
- calculate what can be produced in a fixed press-time window;
- calculate a user-supplied list of production orders in sequence;
- compare the same process, planning request or production sequence across two or more presses;
- work from Python, the command line or JSON.

## What PyExtrusion does not do

PyExtrusion does **not** currently model the full reality of an extrusion plant. In particular, it does not predict or schedule:

- die availability;
- die caustic cleaning / soda treatment;
- die correction or repeated trials;
- die heating or preparation;
- billet availability or logistics;
- shifts, weekends or breaks;
- operator availability;
- maintenance or breakdowns;
- furnace, stretcher, saw or packing bottlenecks;
- automatic order priorities;
- automatic order reordering;
- automatic work allocation between presses;
- complete extrusion-force or thermal-process prediction.

When PyExtrusion calculates a production sequence, the returned time is **continuous technical press time only**. It does not invent time between orders.

## Recommended learning path

If this is your first time using PyExtrusion, follow the guide in this order:

1. [Installation and first steps](getting-started.md)
2. [Define a press](press.md)
3. [Define a profile and process](profile-process.md)
4. [Calculate a process](calculate-process.md)
5. [Plan one production order](planning.md)
6. [Calculate a sequence of orders](production-sequences.md)
7. [Compare presses](compare-presses.md)
8. [Understand the results](understand-results.md)
9. [Use JSON and the CLI](json-cli.md)
10. [Errors and troubleshooting](troubleshooting.md)
11. [Model boundaries](model-boundaries.md)
12. [Glossary](glossary.md)

!!! note "Public documentation"
    This User Guide intentionally documents **how to use and interpret PyExtrusion**. Internal calculation specifications, implementation rules and unpublished engineering documentation are not part of the public guide.


---
