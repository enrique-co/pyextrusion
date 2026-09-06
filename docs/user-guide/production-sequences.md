# Calculate a sequence of production orders

PyExtrusion can calculate a **user-supplied list of production orders in sequence**.

This feature is intentionally simple and deterministic:

> You supply the order. PyExtrusion returns the same order calculated in line.

It does not decide what should run first.

### Create production orders

```python
from pyextrusion import ProductionOrder, PlanningRequest

orders = [
    ProductionOrder(
        "OF-001",
        case_a,
        PlanningRequest.bars(300),
    ),
    ProductionOrder(
        "OF-002",
        case_b,
        PlanningRequest.billets(20),
    ),
    ProductionOrder(
        "OF-003",
        case_c,
        PlanningRequest.kg(2500),
    ),
]
```

### Calculate the sequence

```python
from pyextrusion import calculate_production_sequence

sequence = calculate_production_sequence(
    press,
    orders,
)
```

### What PyExtrusion does

For each order it:

1. calculates the order using the normal planning engine;
2. stores its technical press duration;
3. starts the next supplied order immediately after the previous calculated order;
4. accumulates totals.

Useful outputs include:

```python
sequence.total_planned_billets
sequence.total_planned_bars
sequence.total_planned_good_kg
sequence.total_scrap_kg
sequence.total_press_time_min
sequence.all_orders_fulfilled
sequence.unresolved_order_ids
```

Per order:

```python
sequence.orders[0].order_id
sequence.orders[0].duration_min
sequence.orders[0].cumulative_start_min
sequence.orders[0].cumulative_end_min
sequence.orders[0].planning
```

### Optional theoretical clock time

You can provide a starting date/time:

```python
from datetime import datetime

sequence = calculate_production_sequence(
    press,
    orders,
    start_at=datetime(2026, 9, 7, 5, 0),
)
```

PyExtrusion can then expose theoretical clock timestamps for each order.

These timestamps are **not an industrial schedule**. They assume continuous technical press time.

### No setup or waiting time is invented

PyExtrusion does not insert time for:

- die change;
- die caustic cleaning / soda treatment;
- die correction;
- die heating;
- billet waiting;
- operator breaks;
- shift changes;
- maintenance;
- plant stoppages.

This is deliberate. Such events can vary from minutes to hours or days and cannot be safely guessed from the information available to the calculation engine.

### No automatic reordering

If you send:

```text
OF-001
OF-002
OF-003
```

PyExtrusion returns the sequence in exactly that order.

It does not move `OF-003` ahead of `OF-001`, even if another ordering might appear faster.

### Quantity request restriction

Sequence orders should represent production quantities. Use:

- bars;
- kg;
- metres;
- billets.

Time-window requests (`minutes`, `hours`) are intended for standalone capacity calculations, not as normal production orders inside a sequence.

---
