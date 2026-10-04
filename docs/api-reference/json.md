# JSON workflows

PyExtrusion writes **schema version 1.1**. Historical schemas `0.2` through `1.0` remain readable.

## Canonical trim in 0.19.0

The additive `production.trim_total_per_billet_m` or `process.trim_total_per_billet_m` field means total reject reserve per incoming billet. Omit both legacy trim fields or set them to `null`; any non-null combination is `PX1003`, including zero. Absent trim means zero. A synthetic legacy value `front_scrap_m: 0.6` must explicitly migrate to canonical total `1.2` for its verified two-pull family. Loading legacy JSON does not silently migrate it. The examples below are synthetic **canonical** inputs; [migration instructions](../user-guide/trim-topology.md) cover existing legacy files. Canonical files require 0.19.0 readers; schema 1.1 alone does not imply an older reader accepts new keys.

## Physical butt contract

The JSON input key remains `butt_mm`, in `production` or `process`: physical residual thickness inside the container. Existing physical mm values are not converted by the caller. `null` continues to select the physical default/rule. The physical-butt input key is unchanged; the new trim field described above is additive.

The press field `billet_kg_per_mm_override` still controls the mass per mm of original incoming billet, including billet-saw loss. It does not replace `rho * container_area` for butt mass. When absent or `null`, the incoming-billet coefficient is geometric.

Calculation JSON adds `billet.butt_mass_kg`, `billet.butt_equivalent_billet_mm` and `billet.mass_coefficient_source`. These are output trace fields, not additional inputs. Quantity-free process JSON exposes `butt_mass_kg`, `butt_equivalent_billet_mm` and `billet_mass_coefficient_source`. Existing result fields are retained. Consumers requiring an exact result-key set should accept these additive fields.

## Press JSON

```json
{
  "schema_version": "1.1",
  "press": {
    "name": "Example 8-inch press",
    "nominal_size_in": 8,
    "billet_diameter_mm": 203.2,
    "container_diameter_mm": 210.312,
    "billet_min_length_mm": 450,
    "billet_max_length_mm": 1200,
    "table_length_m": 54,
    "dead_time_sec": 15,
    "density_kg_m3": 2700,
    "saws": {
      "billet_mm": 5,
      "puller_mm": 5,
      "final_mm": 5
    },
    "_provenance": {
      "billet_diameter_mm": "inferred_from_nominal_size",
      "container_diameter_mm": "inferred_from_billet_diameter"
    }
  }
}
```

Serialized press files preserve provenance for inferred/defaulted geometry when applicable.

## StudyCase JSON

```json
{
  "schema_version": "1.1",
  "profile": {
    "linear_weight_kg_m": 1.35,
    "exits": 2,
    "profile_type": "solid",
    "section_per_exit_m2": null
  },
  "production": {
    "exit_speed_m_min": 24,
    "cut_length_mm": 7000,
    "bars_requested": 1000,
    "trim_total_per_billet_m": 2,
    "front_scrap_m": null,
    "complexity": "normal",
    "cuts": null,
    "butt_mm": null,
    "multi_billet_front_scrap_m": null,
    "supplement_10_pct": false,
    "ram_speed_mm_s": null
  }
}
```

A speed can alternatively be supplied as `"ram_speed_mm_s"` with `"exit_speed_m_min": null`. Exactly one speed input must be active.

## PlanningCase JSON

the current planning format deliberately has no order quantity:

```json
{
  "schema_version": "1.1",
  "profile": {
    "linear_weight_kg_m": 1.35,
    "exits": 2,
    "profile_type": "solid",
    "section_per_exit_m2": null
  },
  "process": {
    "exit_speed_m_min": 24,
    "cut_length_mm": 7000,
    "trim_total_per_billet_m": 2,
    "front_scrap_m": null,
    "complexity": "normal",
    "cuts": null,
    "butt_mm": null,
    "multi_billet_front_scrap_m": null
  }
}
```

Use:

```python
from pyextrusion import (
    load_planning_case_json,
    save_planning_case_json,
)
```

Planning output is separate from persisted planning input. `PlanningResult.to_json()` contains a quantity-free `process` object plus an order-level `calculation` object when at least one complete billet is actually planned. If a time window is too short for one billet, `calculation` is `null` while `process` remains available.

For transition compatibility, planning JSON also emits a deprecated `reference` alias containing the same quantity-free process data. New integrations should use `process`.

## ProductionSequence input JSON

A JSON format is available for a user-supplied order list. The sequence uses the existing schema version `1.1`; no new core persistence schema is required.

```json
{
  "schema_version": "1.1",
  "press": {
    "name": "Example 8-inch press",
    "nominal_size_in": 8,
    "billet_diameter_mm": 203.2,
    "container_diameter_mm": 210.312,
    "billet_min_length_mm": 450,
    "billet_max_length_mm": 1200,
    "table_length_m": 54,
    "dead_time_sec": 15,
    "density_kg_m3": 2700,
    "saws": {"billet_mm": 5, "puller_mm": 5, "final_mm": 5}
  },
  "start_at": "2026-09-07T05:00:00",
  "orders": [
    {
      "order_id": "OF-001",
      "case": {
        "profile": {
          "linear_weight_kg_m": 1.35,
          "exits": 2,
          "profile_type": "solid",
          "section_per_exit_m2": null
        },
        "process": {
          "exit_speed_m_min": 24,
          "cut_length_mm": 7000,
          "trim_total_per_billet_m": 2,
          "front_scrap_m": null,
          "complexity": "normal",
          "cuts": null,
          "butt_mm": null,
          "multi_billet_front_scrap_m": null,
          "ram_speed_mm_s": null
        }
      },
      "request": {"mode": "bars", "value": 300}
    }
  ]
}
```

Use:

```python
from pyextrusion import load_production_sequence_json, calculate_production_sequence

press, orders, start_at = load_production_sequence_json("production_sequence.json")
result = calculate_production_sequence(press, orders, start_at=start_at)
```

`start_at` is optional and must be an ISO-8601 datetime string when present. Sequence-order request modes are limited to `bars`, `kg`, `m` and `billets`. `minutes` and `hours` remain standalone planning-capacity requests.

Calculated results can be serialized with `ProductionSequenceResult.to_json()`.

## Result scope

For a calculation result, `process.trim_total_per_billet_m` is per incoming billet and `process.trim_per_pull_m` is the total on a full pull. The `production` block reports `final_saw_events`, `internal_billet_transitions`, `puller_saw_events` and `billet_saw_events` for the actual order, including a partial last group.

A quantity-free process result has top-level trim fields plus `final_saw_events_per_pull` and `internal_billet_transitions_per_pull` for the full-pull configuration. In planning JSON those fields are under `process`; order counters are under `calculation.production` when calculation is non-null. See [result fields](result-fields.md) for exact scopes.

## Compatibility

Current serialized press names use:

- `nominal_size_in`
- `press_force_t`
- `billet_min_length_mm`
- `billet_max_length_mm`
- `density_kg_m3`
- `billet_kg_per_mm_override`

Historical aliases remain readable where documented. `billet_area_m2_override` may be accepted in old files for compatibility but is ignored by the current engine; billet area is derived from `billet_diameter_mm`.


## Strict input handling in schema 1.1

Schema 1.1 writes and expects finite JSON numbers. `NaN`, `Infinity` and `-Infinity` are rejected. Numeric strings such as `"7000"` are not silently converted to numbers, and structural integer fields do not accept fractional values or booleans.

Important ranges include cut length 1000-15000 mm, table length 10-100 m, nominal press size 6-16 in, exit speed 1-100 m/min, dead time 5-30 s, and kerfs of 0 or 3-10 mm.


## Multi-press comparison outputs

PyExtrusion does not require a new persisted input schema for comparisons. It reuses existing press, PlanningCase and production-sequence inputs.

The Python comparison result objects serialize with `to_json()` and include:

```json
{
  "comparison_type": "planning",
  "press_count": 3,
  "automatic_winner": null,
  "results": []
}
```

`automatic_winner` is deliberately `null`: PyExtrusion returns calculated alternatives and does not choose a press for the user.
