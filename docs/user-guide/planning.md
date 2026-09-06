# Plan one production order

`calculate_planning()` applies a production quantity to a previously defined `PlanningCase`.

```python
from pyextrusion import PlanningRequest, calculate_planning

plan = calculate_planning(
    press,
    case,
    PlanningRequest.bars(300),
)
```

### Supported request types

#### Finished bars

```python
PlanningRequest.bars(300)
```

#### Good kilograms

```python
PlanningRequest.kg(2500)
```

#### Good metres

```python
PlanningRequest.metres(1800)
```

`meters()` is also available as an English-US spelling alias where supported by the API.

#### Exact billets

```python
PlanningRequest.billets(20)
```

#### Available press time

```python
PlanningRequest.minutes(90)
PlanningRequest.hours(2)
```

Time-window requests answer a capacity question: how many **complete billets** fit inside the available technical press time?

### Complete billets only

PyExtrusion does not plan fractional billets.

If a request for 300 bars requires 30 billets and those billets produce exactly 300 bars, the result is 300.

If complete-billet rounding produces 308 bars, the result remains 308. PyExtrusion reports the actual planned/manufactured quantity instead of hiding the excess.

### Useful planning outputs

```python
plan.process_supported
plan.process_viable
plan.request_fulfilled

plan.planned_billets
plan.planned_pulls
plan.planned_bars
plan.planned_good_m
plan.planned_good_kg

plan.time_used_min
plan.planned_hours
plan.time_remaining_min
plan.additional_time_for_next_billet_min

plan.planned_fixed_scrap_kg
plan.planned_total_scrap_kg
plan.planned_total_scrap_pct
```

### Example: exactly 20 billets

```python
plan = calculate_planning(
    press,
    case,
    PlanningRequest.billets(20),
)

print(plan.planned_bars)
print(plan.planned_good_kg)
print(plan.planned_pulls)
print(plan.time_used_min)
```

### Example: two hours available

```python
capacity = calculate_planning(
    press,
    case,
    PlanningRequest.hours(2),
)

print(capacity.planned_billets)
print(capacity.planned_bars)
print(capacity.time_used_min)
print(capacity.time_remaining_min)
print(capacity.additional_time_for_next_billet_min)
```

If even one complete billet does not fit into the requested time, the process can still be technically viable while the time request is not fulfilled.

### Operational quantity means what you asked for

Planning requests are literal. If you ask for 300 bars, PyExtrusion treats 300 bars as the target. It does not silently add an annual-demand supplement or safety percentage.

---
