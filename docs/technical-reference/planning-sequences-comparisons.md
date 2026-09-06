# Planning, Sequences & Comparisons

## Planning semantics

PyExtrusion separates the **physical process** from the **quantity requested**.

A process describes how the profile is extruded.

A planning request describes how much output is required.

Public planning requests can be expressed as:

- finished bars;
- good kilograms;
- good metres;
- exact number of billets;
- available technical press time.

### Whole billets

Operational planning works with complete billets.

A request may therefore produce slightly more finished output than the exact requested quantity because the final billet is still manufactured as a whole billet.

### Time-window planning

When a user provides an available press-time window, PyExtrusion determines how many **complete billets** can be completed within that technical time.

It does not count a partially completed billet as finished production.

---


## Production sequences

A production sequence is a user-supplied ordered list of production orders.

PyExtrusion:

- preserves the supplied order;
- calculates each order using the normal planning engine;
- accumulates the technical press time;
- can expose cumulative or theoretical start/end positions.

PyExtrusion does **not**:

- reorder the sequence;
- insert setup assumptions;
- add die-change time;
- add waiting time;
- account for shifts or weekends;
- infer die availability;
- optimise the schedule.

Therefore:

> a production sequence is a continuous technical calculation, not a guaranteed plant schedule.

---


## Multi-press comparison

PyExtrusion can evaluate the same technical case across two or more presses.

The comparison principle is deliberately neutral:

> the same supplied process or production sequence is calculated independently for each press.

The library can expose differences such as:

- viable / not viable;
- supported / unsupported;
- extrusion ratio;
- billet requirement;
- pulls and billets;
- good output;
- process losses;
- technical time;
- net productivity;
- warnings.

PyExtrusion does not automatically select a winner, allocate orders among presses or modify the sequence to improve a result.

---
