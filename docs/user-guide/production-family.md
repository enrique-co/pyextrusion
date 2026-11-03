# Choose a production family

This feature is available on the development branch as **0.20.0.dev0 (unreleased)**. It is not part of the published 0.19.0 release.

`ProcessSpec` and `ProductionSpec` accept two optional inputs:

| Input | Meaning |
| --- | --- |
| `configuration=None` | Preserve the automatic selection used by 0.19.0. |
| `configuration="1_billet_1_profile"` | One billet produces one pull. |
| `configuration="1_billet_2_profiles"` | One billet produces two sequential pulls. These are not two die exits. |
| `configuration="k_billets_1_profile", billets_per_pull=k` | Exactly `k` billets contribute to one continuous pull. `k` must be an integer of at least two. |

Do not supply `billets_per_pull` for the other families or for automatic selection. Booleans, numeric strings and floating-point counts are rejected. Changing from a multibillet family to another family requires explicitly clearing that input.

## Reduce cuts without changing topology

The following synthetic example keeps one pull per billet while changing commercial cuts:

```python
from pyextrusion import (
    PressSpec, SawSpec, ProfileSpec, ProcessSpec, PlanningCase,
    PlanningRequest, calculate_planning,
)

press = PressSpec(
    name="Example press", nominal_size_in=9,
    billet_diameter_mm=228, container_diameter_mm=236,
    billet_min_length_mm=400, billet_max_length_mm=1300,
    table_length_m=60, dead_time_sec=15,
    billet_kg_per_mm_override=0.110, saws=SawSpec(0, 0, 0),
)
profile = ProfileSpec(linear_weight_kg_m=1.8, exits=1, profile_type="solid")
case = PlanningCase(profile, ProcessSpec(
    exit_speed_m_min=25, cut_length_mm=6000,
    trim_total_per_billet_m=3, butt_mm=20,
    configuration="1_billet_1_profile", cuts=8,
))

for cuts in (8, 7, 6):
    result = calculate_planning(
        press, case.with_process(cuts=cuts), PlanningRequest.bars(160),
    )
    assert result.process_viable
    assert result.selected_configuration == "1_billet_1_profile"
    print(cuts, result.billet_length_mm, result.planned_billets)
```

The billet length is calculated from the adopted physical production concept. It is not an independently selected input. Reducing cuts can eventually put the billet below the press minimum; that choice is returned as nonviable. This selection does not assess die strength.

For `p=1`, `cuts` is the number of commercial positions per billet contribution and exit. For `p=2`, it is per sequential pull and exit. Thus six cuts with two sequential pulls and one exit produce twelve bars per billet. The number of exits does not multiply transverse saw-event counts.

With a fixed multibillet count, reducing cuts does not add billets to fill the table. With `cuts=None`, the engine optimizes cuts within the requested family and exact multibillet count.

## Recommendation and actual result

Use `selected_configuration` for the family used by geometry, quantities, losses, time and productivity. `configuration_source` is `"automatic"` or `"user_override"`.

`recommended_configuration` and `automatic_recommendation` describe the original automatic policy **for the same process inputs, including the current cuts**. They do not represent a separate optimization with the manual cuts removed. The full automatic candidate includes its billet length and multiplicities.

`requested_configuration_result` contains the explicitly requested candidate, including physical rejection reasons. It remains available when the request is not viable. In that case:

- `viable` / `process_viable` is false;
- `selected_configuration` is null;
- order planning has no calculation and no planned bars or billets;
- a viable automatic recommendation may still be shown, but is not used as a fallback.

These fields are available in process and calculation results, JSON, trace/status blocks and planning summaries. Comparison-table configuration columns show the adopted family. The rounded-up `recommended_billet_length_mm` remains the billet sizing recommendation **for the adopted concept**, not the separate automatic candidate.

## Planning and partial pulls

The selection is propagated through bars, kg, metres, exact billets, time windows and production-order sequences. A last partial multibillet pull retains the requested grouping for complete pulls; it contains only the remaining actual billets. It is not padded with extra production.

Explicit-selection time windows use the canonical calculation of each candidate order, including the actual shared saw events of a partial last pull. Times reported by the plan and its calculation agree. The pre-existing automatic-mode path is retained for compatibility with 0.19.0.

Canonical trim remains the total per incoming billet, including both sequential pulls when `p=2`. Butt physics, saw kerfs and press limits retain their existing meanings. No additional final-saw operating time is introduced.

## Save and load

Selected cases are written with JSON `schema_version="1.2"`; process/study conversion, sequences and JSON loaders retain both selector inputs. Cases without an explicit selection keep the previous schema 1.1 and omit the new input keys.

An explicit selection cannot be saved or loaded as schema 1.1 or earlier. Older PyExtrusion releases reject schema 1.2 instead of treating the case as automatic. In sequences the outer schema is 1.2 if any order is selected; nested cases preserve the applicable version.

`process_from_dict` remains a low-level constructor for a process dictionary and has no case-level schema envelope. Use the case JSON helpers when persisting a complete case.

The CLI accepts these inputs through case JSON for `plan`, `calc`, `annual`, comparisons and sequences. No separate CLI flags override the saved family.

To restore automatic mode on an existing case, explicitly clear both selector inputs:

```python
automatic = case.with_process(configuration=None, billets_per_pull=None)
```
