# User Guide

Use this guide to learn PyExtrusion 0.18.0 from a practical, task-oriented
point of view. The package now covers three related areas: production and
planning, bounded analytical engineering tools, and deterministic economics.

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
- evaluate source-traced AA6063 and AA6060 constitutive models;
- calculate equivalent-axisymmetric mechanical baselines and bounded thermal
  analytical results;
- calculate recurring production cost, material/scrap economics,
  tooling/development cost and sales margins;
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
- final shaped-section, bridge-die or porthole-die force prediction;
- production-grade exit-temperature prediction.

When PyExtrusion calculates a production sequence, the returned time is **continuous technical press time only**. It does not invent time between orders.

## Recommended learning paths

Start with installation, then follow the path that matches your task.

### Production & Planning

1. [Installation and first steps](getting-started.md)
2. [Define a press](press.md)
3. [Define a profile and process](profile-process.md)
4. [Calculate a process](calculate-process.md)
5. [Plan one production order](planning.md)
6. [Calculate a sequence of orders](production-sequences.md)
7. [Compare presses](compare-presses.md)
8. [Understand the results](understand-results.md)

### Engineering

1. [Engineering overview](../engineering/index.md)
2. [Materials and rheology](../engineering/materials-rheology.md)
3. [Mechanical baseline](../engineering/mechanical-baseline.md)
4. [Thermal boundaries](../engineering/thermal-boundaries.md)
5. [Engineering API](../api-reference/engineering.md)

### Economics

1. [Basic economics](basic-economics.md)
2. [Economics API](../api-reference/economics.md)

For every path, also review [JSON and the CLI](json-cli.md),
[troubleshooting](troubleshooting.md), [model boundaries](model-boundaries.md)
and the [glossary](glossary.md) as needed.


---
