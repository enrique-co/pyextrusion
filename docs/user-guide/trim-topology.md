# Trim topology and legacy migration

**PyExtrusion 0.19.0**. This is a physical behavior and public-input contract change, not a silent replacement of 0.18.0 results.

## Canonical input

`trim_total_per_billet_m` is the **total trim/reject length attributed to one incoming billet**, in metres of extrudate per exit. It is an industrial rejection policy, not only front trim, and not a universal metallurgical charge-weld length. PyExtrusion does not predict charge-weld extent or weld quality.

For one billet producing `p` sequential pulls, each contribution receives `d_total/p`. For example, a synthetic `1.2 m/billet` reserve is distributed as `0.6 + 0.6 m`, not `1.2` per pull. Trim mass is `N_B * d_total * combined_linear_weight`; do not multiply this total by `p` again.

```python
from pyextrusion import Process

process = Process(18, 4000, cuts=3, butt_mm=25,
                  trim_total_per_billet_m=1.2)
```

## Physical diagrams and final-saw boundaries

For positive reject reserve, each billet commercial block has half of its allocated trim before it and half after it. `|` below denotes a final-saw event; the block includes one kerf between each adjacent commercial bar.

```text
1 billet -> 1 pull:
  d/2 | bar | ... | bar | d/2 -> puller cut

2 billets -> 1 continuous pull:
  d/2 | bars | d/2 UNION d/2 | bars | d/2 -> puller cut
  The two adjacent half-reserves form the rejected internal zone.

1 billet -> 2 sequential pulls (total d):
  pull 1: d/4 | bars | d/4 -> puller cut
  pull 2: d/4 | bars | d/4 -> puller cut
  Total reject d, one physical butt for the incoming billet.
```

With `n_c` commercial bars per contribution and exit, final kerf `k_f`, and puller kerf `k_p`, all in metres:

```text
L_contribution = n_c L_c + d_contribution + (n_c + 1) k_f
L_pull = sum(actual contributions) + k_p
N_final = p N_B (n_c + 1)                  [positive reject policy]
N_internal = sum(k_j - 1) = N_B - N_pulls  [p = 1]
N_final = N_B n_c + N_pulls + N_internal   [p = 1]
          commercial + pull boundary + internal boundaries
```

For `k` billets and p=1, rejected length is `d/2 + (k-1)d + d/2 = k*d`. The union marker itself does not add a further saw event. A transverse stroke acts on all simultaneous exits; events are **not** multiplied by exits, while kerf mass uses their combined linear weight.

Synthetic examples: two billets with three commercial positions each produce **8** final-saw events per full pull. Three billets with three positions each produce **12** final events, two internal transitions and one puller event. Exits affect mass and bar count, not the transverse event count.

## Partial last pull, zero kerf and zero trim

Count actual groups, never `N_pulls * (nominal_k-1)`. For a synthetic two-exit process with three commercial positions, a request for 13 bars requires three billets. With capacity for two billets per pull, the actual groups are `2+1`: 12 final-saw events and one internal transition.

Zero final kerf removes kerf length and mass, **not** the declared event topology.

With zero trim the positive-reject topology is not assumed. The engine retains the historical one end-preparation final-kerf allowance per actual pull, plus one per commercial position: `N_final = p N_B n_c + N_pulls`. No extra internal rejection boundaries are added. This compatibility convention does not assert metallurgical acceptability of an untrimmed billet union. `trim_topology` explicitly distinguishes these policies.

The process-level billet recommendation represents a full pull. Exact partial-pull loss/time accounting can require plant-specific last-billet length adjustment; the engine reports that limitation. Feasibility uses unrounded geometry, never the displayed or ceil-recommended billet length.

## Time and protected models

Additional final kerf is physically extruded metal: it changes through-die length/mass, billet sizing, loss, extrusion time and net productivity. It does **not** add a saw-operation time or a new press delay. For p=1, press dead events remain `N_B-1`; the existing p=2 rule is unchanged. Butt, upsetting, constitutive, pressure and thermal equations are unchanged. Mechanical screening changes only through the billet/contact length when geometry changes. No final shaped/porthole force or production-grade exit-temperature predictor is introduced.

## Legacy API and JSON migration

Legacy `front_scrap_m` keeps its 0.18.0 meaning:

| Selected known family | Legacy value | Canonical total |
|---|---:|---:|
| p=1, k=1 or multibillet | d per billet | d |
| p=2 sequential pulls | d per pull | 2d |
| Synthetic p=2 example | 0.6 | 1.2 |

Legacy loading is **not** automatic migration. A legacy calculation emits a diagnostic warning and identifies its semantics. Its multibillet event physics is corrected in 0.19.0; backward input compatibility does not preserve the former multibillet event counts.

```python
from pyextrusion import load_case_json, migrate_legacy_trim, save_case_json

legacy = load_case_json("legacy_split.json")
# Explicitly supply the verified old family, not a guessed family:
canonical = migrate_legacy_trim(legacy, profiles_per_billet=2)
save_case_json(canonical, "canonical_split.json")
```

The helper also accepts `PlanningCase`. It preserves the original immutable object. If a legacy `multi_billet_front_scrap_m` override exists, explicitly pass `use_multi_billet_override=True` or `False` according to the verified old selection. The override may apply only for p=1. Migrating an already canonical case is rejected. Recalculate on the intended press and compare the selected family and outputs; migration does not promise unchanged automatic selection on a different press.

Do **not** rename the old field blindly. Do **not** supply canonical trim alongside either non-null legacy input, even legacy `0.0`: the controlled error is `PX1003`. `None`/JSON `null` means absent. If all trim inputs are absent, total trim is zero. Default legacy dataclass fields now have value `None`, not `0.0`, so serializers can distinguish omission from explicit zero.

JSON remains additive schema `1.1`; the canonical field itself identifies the new semantics. Older PyExtrusion readers cannot consume that new field and should reject it rather than reinterpret it. Newly written 0.19.0 files may include the additive field even as null and use null for omitted legacy inputs; they are not promised to be writable back to 0.18.0. Retain the original legacy file for older software.

## Results, diagnostics and CLI

Python and JSON expose `process.trim_total_per_billet_m`, `process.trim_per_pull_m` (full pull), `process.trim_input_semantics`, and `process.trim_topology`. Quantity-free process/configuration results also expose per-full-pull final-event and internal-transition counts. Order results expose:

- `production.final_saw_events`;
- `production.internal_billet_transitions`;
- `production.puller_saw_events`;
- `production.billet_saw_events`.

`cuts`/`cuts_per_pull` are commercial positions, not physical event totals. Compatibility names `front_scrap_per_billet_m` and `applied_front_scrap_m` project the reserve per contribution to one pull; for p=2 they are half the total per billet. `front_scrap_kg` already means the whole order's rejected mass. Legacy `standard_front_scrap_m` is zero when no legacy input is present; it is not the canonical total.

```bash
pyextrusion calculate canonical_split.json --press press.json --field process.trim_total_per_billet_m
pyextrusion calculate canonical_split.json --press press.json --field production.final_saw_events
pyextrusion field process.trim_input_semantics
```
