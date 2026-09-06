# Compare two or more presses

PyExtrusion can apply the **same technical input** to two or more presses and return the calculated alternatives.

It does not choose a winner.

### Compare a process

```python
from pyextrusion import compare_processes

comparison = compare_processes(
    [press_a, press_b, press_c],
    case,
)
```

This answers questions such as:

> How does the same profile/process fit each press before I decide on a production quantity?

### Compare one planning request

```python
from pyextrusion import compare_planning, PlanningRequest

comparison = compare_planning(
    [press_a, press_b, press_c],
    case,
    PlanningRequest.bars(300),
)
```

Each press receives the same profile, process and request.

Typical comparison values include:

- supported / viable state;
- billets;
- pulls;
- bars;
- good kg;
- billet length;
- scrap;
- technical press time;
- productivity-related outputs.

### Compare a complete sequence

```python
from pyextrusion import compare_production_sequences

comparison = compare_production_sequences(
    [press_a, press_b, press_c],
    orders,
)
```

Every press receives:

- the same complete order list;
- in the same order;
- with the same quantity requests.

### What comparison does not do

PyExtrusion does not:

- rank the presses automatically;
- declare a best press;
- split orders between presses;
- load-balance work;
- reorder the production sequence;
- model press availability.

The user or consuming application decides what to do with the calculated alternatives.

### Why no automatic winner?

A real industrial choice can depend on factors outside the calculation engine: die availability, alloy campaign, maintenance state, customer priority, operator constraints, downstream equipment and many other plant-specific considerations.

PyExtrusion therefore returns engineering information rather than hiding a plant decision behind a single automatic score.

---
