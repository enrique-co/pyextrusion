# Examples

The `examples/` directory contains runnable Python and JSON examples.

`examples/trim_migration.py` demonstrates a synthetic canonical total `1.2 m/billet` and its unchanged physical results. Earlier examples retain `front_scrap_m` deliberately as legacy inputs; do not blindly rename that field, especially for p=2. See [trim topology and migration](../user-guide/trim-topology.md).

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
adjusted = case.with_production(butt_mm=25)  # Physical thickness in the container.
```

Without an override, PyExtrusion uses 15 mm for solid/plate and 20 mm for hollow/tubular.

Do not convert these values to incoming-billet length before calling the engine. Inspect `result.billet.butt_mass_kg`, `result.billet.butt_equivalent_billet_mm` and `result.billet.mass_coefficient_source` to trace the conversion. A measured `billet_kg_per_mm_override` affects the incoming-billet equivalent and upstream billet saw, but the physical butt mass still uses the container section and density.

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

## Engineering screening

The [Engineering API example](../api-reference/engineering.md) provides a
complete, runnable chain from modified Feltham mean strain rate through
Zener-Hollomon, flow stress, pressure and `F_baseline`. It also keeps the Stüwe,
Saha and interface-temperature calls separate so their different boundaries
remain visible.

## Production economics

The [Economics API example](../api-reference/economics.md) calculates recurring
production cost, material and scrap effects, first-run tooling/development cost
and sales margin from explicit assumptions.
