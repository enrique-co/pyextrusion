# Changelog

## Unreleased

- Corrects the physical process boundary for downstream saw kerfs.
- Treats `cut_length_mm` as net finished-bar length; puller and final-saw kerfs now reserve additional extruded material instead of being added only after billet sizing.
- Propagates puller/final-saw kerf allowance into billet geometry, runout-table occupancy and technical extrusion time.
- Keeps billet-saw kerf as an upstream billet-stock loss rather than extrusion length.
- Uses exact order-level puller/final-saw event counts for technical time, including partial final multi-billet pulls.
- Adds a controlled warning when a partial multi-billet pull can require plant-specific billet-length handling beyond the complete-pull process recommendation.
- Reframes startup and complexity as modeled planning allowances: they remain in total modeled scrap but no longer inflate the physical `extruded_losses_kg` / real-gross extrusion boundary or extrusion time.
- Adds physical mass/time balance regression coverage for one-pull, double-profile and multi-billet cases.
- This correction can slightly increase calculated billet length and technical time for processes with non-zero downstream saw kerfs.

## 0.16.0

- Aligns the multi-press comparison layer with the current PyExtrusion calculation engine.
- Adds `compare_processes()` for quantity-free process comparison across two or more presses.
- Adds `compare_planning()` for one explicit `PlanningRequest` across two or more presses.
- Adds `compare_production_sequences()` for the exact same ordered production list across two or more presses.
- Adds `ProcessComparisonResult`, `PlanningComparisonResult` and `ProductionSequenceComparisonResult`.
- Preserves press order and sequence order exactly.
- Performs no automatic ranking, winner selection, order allocation, load balancing or sequence optimisation.
- Adds strict JSON output and human-readable formatters for all three new comparison layers.
- Adds CLI `compare-process`, `compare-planning` and `compare-sequence`.
- Adds `PX1013 InvalidComparison`.
- Keeps JSON input schema `1.1`; existing press, planning-case and sequence input formats are reused.
- Does not change the v0.15.0 physical, billet-first, scrap, productivity, planning or sequence mathematics.



## 0.15.0

- Adds the public production-sequence layer on top of the existing planning API.
- Adds `ProductionOrder`, `ProductionSequenceEntry`, `ProductionSequenceResult` and `calculate_production_sequence()`.
- Preserves the exact user-supplied order; no automatic sequence optimisation or sorting is performed.
- Chains only existing planning time (`extrusion + technical dead time`) and inserts no setup, die-change, waiting, die-preparation, correction, maintenance or calendar assumptions.
- Supports sequence-order quantities in bars, kg, metres and exact billets.
- Rejects minutes/hours as sequence-order quantities; they remain planning capacity-window requests.
- Adds optional theoretical timestamps from a user-supplied `datetime`; without `start_at`, only relative cumulative minutes are returned.
- Keeps unresolved orders in place with diagnostics and zero calculable duration so the caller can decide what to do.
- Adds aggregate sequence totals for billets, pulls, bars, metres, good kg, scrap and technical press time.
- Adds strict JSON serialization for calculated sequence results and a human-readable sequence formatter.
- Adds `PX1012 InvalidProductionSequence`.
- Does not change v0.14.0 physical, billet-first, scrap, productivity or single-order planning mathematics.

## 0.14.0

- Consolidates the quantity-free planning API.
- Adds public `calculate_process(press, PlanningCase)` returning `ProcessResult` without any order quantity.
- `calculate_planning()` no longer creates a fictitious one-bar study to resolve billet, cuts, configuration or table occupancy.
- Adds `PlanningResult.process` as the canonical quantity-free process reference.
- Keeps `StudyCase` planning support only as a compatibility bridge and emits a deprecation warning.
- Adds direct planning outputs for optimized billet length, table occupancy and fixed/total scrap.
- Time-window planning creates a full order `CalculationResult` only when at least one complete billet is actually planned.
- Keeps JSON schema `1.1`; no persistence-schema change is required.
- Does not change the existing physical/productivity mathematics for equivalent valid inputs.

## 0.13.1

- Hardens input validation and public interfaces.
- Restricts nominal press size to strict whole-inch values from 6 to 16.
- Enforces configurable billet lengths of 100-3000 mm and runout tables of 10-100 m.
- Enforces finished cut lengths of 1000-15000 mm and rejects cuts longer than the table.
- Enforces exit/profile speed of 1-100 m/min and adds `ram_speed_mm_s` as an alternative process input.
- Rejects simultaneous exit-speed and ram-speed inputs as ambiguous; ram-input calculations derive and validate exit speed through volume constancy.
- Enforces technical dead time of 5-30 s and saw kerfs of 0 or 3-10 mm.
- Makes exits, manual cuts, requested bars, requested billets and nominal press size strict integers; rejects booleans, fractional counts and numeric strings.
- Rejects NaN, Infinity and non-finite intermediate values and writes strict JSON with schema `1.1`.
- Keeps schemas `0.2` through `1.0` readable, including migration of historical whole-valued float nominal press sizes.
- Hardens file/JSON errors into documented PX errors instead of predictable raw tracebacks.
- Replaces automatic cut enumeration with direct bounded billet-first integer limits to prevent resource-exhaustion inputs.
- Adds `geometry.exit_speed_m_min` and `process.speed_input_source` to the public result glossary (98 fields).
- Does not change the v0.13.0 calculation mathematics for inputs that remain valid under the new validation rules.

## 0.13.0

- Introduces dynamic multi-billet behaviour and the quantity-free planning architecture.
- Replaces the historical fixed `2_billets_1_profile` / `3_billets_1_profile` model with dynamic `k_billets_1_profile`.
- Implements billet-first optimisation: the longest valid billet is selected before `billets_per_pull` is derived from table length.
- Prevents the optimiser from shortening a billet merely to fit more billets on the runout table.
- Allows 4, 5 or more billets per continuous pull when geometry permits.
- Keeps `1_billet_2_profiles` and explicitly limits the supported model to a maximum of two sequential profiles per billet.
- Adds controlled `supported=False` diagnostics when a scenario would require 3+ profiles/billet.
- Counts multi-billet puller and final-saw losses per pull, including partial final pulls.
- Corrects multi-billet `cuts_ratio` to use cuts represented by the complete table-occupying pull.
- Adds `ProcessSpec` / `Process` and `PlanningCase` so process conditions can be defined independently from order quantity.
- Keeps `StudyCase` accepted by planning for backwards compatibility.
- Adds PlanningCase JSON load/save/validation and CLI planning support for quantity-free process files.
- Bumps current JSON write schema to `1.0`; schemas `0.2` through `0.9` remain readable.
- Expands the documented result glossary to 96 structured fields, including support status and pull-grouping fields.
- Adds regression coverage for dynamic k, billet-first behaviour, partial pulls, pull-level saw accounting, unsupported 3+ profiles/billet and PlanningCase workflows.

## 0.12.0

- Adds the first operational production-planning layer for daily and short/medium batch calculations.
- Adds `PlanningRequest`, `PlanningResult`, `calculate_planning()` and `format_planning_result()`.
- Supports explicit planning targets in bars, kg, metres and exact billet count.
- Supports available press-time windows in minutes or hours and returns the maximum number of complete billets that fit.
- Reports planned billets, bars, good metres, good kg, used time, remaining time and extra time required for the next billet.
- Planning uses complete billets only; fractional billets are never created.
- Planning does not apply the annual `supplement_10_pct` implicitly; an explicit operational target remains exact.
- Adds CLI `pyextrusion plan` for bars, kg, metres, billets, minutes and hours.
- Adds documented `PX1011 InvalidPlanningRequest`.
- Adds planning documentation and a runnable public planning example.
- Keeps the existing core formulas, JSON schema 0.9, provenance rules and all 0.11.2 calculation behavior unchanged.

## 0.11.2

- Fixes `1_billet_2_profiles` validation so an individual sequential pull cannot exceed `table_length_m`; sequential pulls do not occupy the table simultaneously, but each complete pull must fit.
- Adds a regression test covering manual cuts that exceed the runout-table length.
- Corrects the integration guides to state that JSON schema `0.9` is the current write format.
- Clarifies README and documentation availability for wheel-only users.
- No other calculation formulas, defaults, JSON schema, provenance rules, or productivity-index behaviour changed from v0.11.1.

## 0.11.1

- Fixes press JSON provenance round-tripping: inferred press values remain identified as inferred after save/load instead of being relabelled as `user_value`.
- Adds `_provenance` metadata to serialized press objects while keeping `Press.to_dict()` configuration-only for API compatibility.
- Preserves provenance in standalone press JSON and embedded study JSON.
- Bumps JSON output schema to `0.9`; schemas `0.2` through `0.8` remain readable.
- No calculation formulas, industrial defaults, productivity-index behaviour or complexity behaviour changed from v0.11.0.

## 0.11.0

- Refactors the calculation engine into the generic direct-extrusion model used by current PyExtrusion.
- Reframes the engine as a generic model for **direct aluminium extrusion presses**.
- Adds `nominal_size_in` press definition and documented inference of billet diameter, container diameter, billet-length limits and reference productivity.
- Makes `table_length_m` mandatory and keeps `press_force_t` optional.
- Changes extrusion ratio and ram-speed calculations to use **container-bore area**.
- Keeps actual billet area for billet mass, kg/mm and billet-length calculations.
- Retires the historical billet-area override from active v2.0 calculations; actual billet diameter now always defines billet area, while `billet_kg_per_mm_override` remains available for measured mass coefficients.
- Changes default butt discard to 15 mm for solid/plate and 20 mm for hollow/tubular.
- Changes default saw kerfs to 5/5/5 mm; `0` kerf explicitly means no material loss for that saw operation.
- Keeps 15 s as default dead time.
- Keeps complexity levels `normal`/`medium`/`high` at 3/5/7%, with `normal` default.
- Keeps the documented startup-scrap rule.
- Adds a reference-productivity heuristic based on nominal press size, with user value taking priority.
- Adds percentage-based productivity deficit and penalty.
- Adds an orientative 0-100 productivity index and rating.
- Adds mathematical and upward-rounded recommended billet lengths.
- Adds container/billet area separation to structured results.
- Suppresses downstream geometry/productivity warnings when a case is completely non-viable with `cuts=0`.
- Removes the old recommended minimum linear-weight concept from the public configuration.
- New JSON output schema is `0.8`; schemas `0.2` through `0.7` remain readable.
- New serialised press names use `press_force_t`, `billet_min_length_mm`, `billet_max_length_mm`, `density_kg_m3`, and `billet_kg_per_mm_override` while historical aliases remain accepted.
- Public structured field glossary expands to 82 fields.
- Direct calculation validation now raises the documented PX1001/PX1002/PX1003 error classes for press/profile/production input failures.

## 0.10.0

- Added RE status thresholds: solid/plate low <25, OK 25-85, high >85; hollow/tubular low <15, OK 15-75, high >75.
- Added the explicit optional `supplement_10_pct` demand flag, disabled by default.
- Applied the 10% supplement before annual-demand normalization.
- Removed the old automatic warning based on `extra_pct < 10%`.
- Redefined `extra_pct` as complete-billet rounding excess relative to the effective bar target.
- Added base/effective demand trace fields and CLI supplement overrides.
- Bumped JSON schema output to 0.7 while retaining backward compatibility with 0.2-0.6.

## 0.9.0

- Corrected bars per billet using `cuts × exits × profiles_per_billet`.
- Corrected billet count and manufactured quantity for the double-profile configuration.
- Corrected front-scrap, puller-saw and final-saw losses to account for two complete pulls per billet.
- Kept butt-discard and billet-saw losses once per billet.
- Kept the extra dead-time event per billet for `1_billet_2_profiles`.
- Added `production.profiles_per_billet` to the public result contract.
- Made `profile_type` mandatory for new profiles/cases.
- Added public aliases: `solid`, `plate`, `hollow`, `tubular`; aliases normalize to `solid`/`hollow` internally.
- Missing or invalid profile types raise `PX1002` with the valid values listed.
- Bumped current JSON schema version to `0.6`.

## 0.8.0

- Added the official result-field glossary with exact path, unit, data type and description.
- Added `FieldInfo`, `FIELD_GLOSSARY`, `list_fields()` and `describe_field()`.
- Added CLI `pyextrusion fields` and `pyextrusion field <path>`.
- Added immutable StudyCase derivation helpers: `with_profile()`, `with_production()` and flat `replace()`.
- Added stable documented errors `PX1001` through `PX1010` and public `PyExtrusionError` subclasses.
- Added `ERROR_CATALOG`, `get_error_info()` and `list_error_info()`.
- Added CLI `pyextrusion errors` and `pyextrusion error <code>`.
- Validation messages now include relevant PX codes for errors.
- CLI scalar output keeps Python numeric precision by design.

## 0.7.0

- Added structured result blocks for geometry, billet, production, scrap, productivity, timing and process trace.
- Exposed the complete scrap breakdown.
- Added `CalculationResult.value()`, `select()`, `section()`, `field_paths()` and dotted-path `__getitem__`.
- Added CLI `--field`, `--fields` and `--section` result selectors.
- Added butt-discard and front-scrap provenance.
- Added documented warnings for low cuts ratio, fixed scrap above 12%, and <=3 bars/billet.
- Preserved legacy flat result attributes for backwards compatibility.

## 0.6.0

- Adopted the Apache License 2.0 as the official project license.
- Added `LICENSE`, `NOTICE`, `AUTHORS.md` and `CITATION.cff`.
- Established **Enrique Calvo Ordonez** as project creator and lead author.
- Established **https://pyextrusion.com** as the official project website.
- Added `pyextrusion info` for version, description, author, license and website.

## 0.5.0

- Added annual demand normalization for kg/year, metres/year and bars/year.
- Added `AnnualDemandSpec`, `NormalizedAnnualDemand` and `AnnualCalculationResult`.
- Added `calculate_annual_demand()` and `normalize_annual_demand()`.
- Added annual demand JSON load/save helpers.
- Added `pyextrusion annual` CLI command.
- Added MkDocs + Material documentation source.

## 0.4.0

- Added `ProductionSpec` / `Production` and reusable `StudyCase`.
- Added `calculate_case()` to run one case on any press.
- Added `compare_presses()` and `ComparisonResult`.
- Added standalone press and case JSON persistence.
- Added human-readable press, result and comparison reports.
- CLI gained external press files and multi-press comparison.

## 0.3.0

- Added all four documented billet/profile configurations.
- Added multi-billet front-scrap recalculation.
- Added special dead-time rule for `1_billet_2_profiles`.
- Separated total extruded/configuration length from runout-table occupancy.

## 0.2.0

- Added `Press` and `Profile` friendly aliases.
- Added `calculate_simple()`.
- Added JSON schema support and validation.
- Added structured validation messages.
- Profile section inference uses press-configured aluminium density.

## 0.1.0

- Initial calculation-core development preview.
