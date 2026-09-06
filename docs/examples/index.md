# Examples

The `examples/` directory contains runnable Python and JSON examples.

## Minimal press from nominal size

```python
from pyextrusion import Press

press = Press(
    name="Example 8-inch press",
    nominal_size_in=8,
    table_length_m=54,
)
```

## Real plant dimensions

```python
press = Press(
    name="Example 9-inch press",
    nominal_size_in=9,
    billet_diameter_mm=228,
    container_diameter_mm=236,
    billet_min_length_mm=500,
    billet_max_length_mm=1300,
    table_length_m=64,
    dead_time_sec=14,
    target_net_productivity_kg_h=2200,
)
```

## No billet saw loss

```python
from pyextrusion import SawSpec

press = Press(
    name="Press with billet shear",
    nominal_size_in=8,
    table_length_m=54,
    saws=SawSpec(billet_mm=0, puller_mm=5, final_mm=5),
)
```

## Manual butt override

```python
adjusted = case.with_production(butt_mm=25)
```

Without an override, PyExtrusion uses 15 mm for solid/plate and 20 mm for hollow/tubular.

## Compare presses

```python
from pyextrusion import compare_presses

comparison = compare_presses([press_8, press_9], case)
for result in comparison.results:
    print(result.press_name, result.real_net_kg_h, result.productivity_index)
```

The productivity index is orientative; the final industrial decision remains with the user.


## Operational planning

`examples/planning.py` shows three day-to-day planning questions using the same profile/case:

- produce 300 bars;
- extrude exactly 20 billets;
- calculate the capacity of a two-hour press window.

Run it with:

```bash
python examples/planning.py
```

## Production sequence

`examples/production_sequence.py` calculates three user-supplied orders in sequence, preserves their order and optionally derives theoretical clock timestamps from a supplied `datetime`.

```bash
python examples/production_sequence.py
```

## Multi-press comparison

```bash
python examples/multi_press_comparison.py
```

This example applies one process, one planning request and one complete order sequence to several presses without ranking or allocating work.
