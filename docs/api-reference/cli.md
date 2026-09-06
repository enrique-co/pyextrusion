# Command line interface

PyExtrusion includes a CLI for engineers, scripts and AI/tool integrations.

## Identity and version

```bash
pyextrusion --version
pyextrusion info
```

## Validate JSON

```bash
pyextrusion validate press.json
pyextrusion validate case.json
pyextrusion validate annual_demand.json
pyextrusion validate planning_case.json --kind planning
pyextrusion validate production_sequence.json --kind sequence
```

Validation errors include their documented PX code, for example:

```text
ERROR   PX1003 production.exit_speed_m_min: must be between 1 and 100 m/min
```

## Official result-field glossary

```bash
pyextrusion fields
pyextrusion fields --section scrap
pyextrusion field production.bars_manufactured
pyextrusion field scrap.total_kg --format json
```

Field names are exact API identifiers. Use the glossary instead of guessing synonyms.

## Error catalog

```bash
pyextrusion errors
pyextrusion error PX1004
pyextrusion error PX1004 --format json
```

## Inspect a press

```bash
pyextrusion press show press.json
```

## Calculate

```bash
pyextrusion calculate case.json --press press.json
```

Complete JSON:

```bash
pyextrusion calculate case.json --press press.json --format json --pretty
```

One raw scalar value (Python numeric precision is preserved):

```bash
pyextrusion calculate case.json --press press.json --field scrap.total_kg
```

One section:

```bash
pyextrusion calculate case.json --press press.json --section scrap --format json --pretty
```

Several exact fields:

```bash
pyextrusion calculate case.json --press press.json \
  --fields scrap.total_kg productivity.real_net_kg_h billet.length_mm \
  --format json --pretty
```


## Operational production planning

```bash
pyextrusion plan planning_case.json --press press.json --bars 300
pyextrusion plan planning_case.json --press press.json --billets 20
pyextrusion plan planning_case.json --press press.json --hours 2
```

Other supported targets:

```bash
pyextrusion plan planning_case.json --press press.json --kg 2500
pyextrusion plan planning_case.json --press press.json --metres 1800
pyextrusion plan planning_case.json --press press.json --minutes 90
```

Planning works with complete billets and uses only extrusion time plus the technical dead time currently modeled by PyExtrusion. `StudyCase` JSON remains accepted by the plan command as a compatibility bridge; planning emits a deprecation warning and `PlanningCase` JSON is preferred.

## Production sequences

```bash
pyextrusion sequence production_sequence.json
pyextrusion sequence production_sequence.json --format json --pretty
```

The command preserves the list order exactly and chains only the technical press time calculated for each order. No setup, die-change, waiting or calendar time is inserted.

## Compare presses

Legacy study/cotization comparison:

```bash
pyextrusion compare case.json press_a.json press_b.json press_c.json
```

Quantity-free process comparison:

```bash
pyextrusion compare-process planning_case.json press_a.json press_b.json press_c.json
```

Operational planning comparison:

```bash
pyextrusion compare-planning planning_case.json press_a.json press_b.json --bars 300
pyextrusion compare-planning planning_case.json press_a.json press_b.json --hours 2
```

Exact same production sequence on several presses:

```bash
pyextrusion compare-sequence production_sequence.json press_a.json press_b.json press_c.json
```

The new comparison commands require at least two presses and never rank them or select an automatic winner.

## Annual demand

```bash
pyextrusion annual case.json --press press.json --demand annual_demand.json
```

or:

```bash
pyextrusion annual case.json --press press.json --value 20000 --unit kg
```

## Recalculate with a 10% demand supplement

```bash
pyextrusion calculate case.json --press press.json --supplement-10-pct
pyextrusion annual case.json --press press.json --value 10000 --unit kg --supplement-10-pct
```

Disable a supplement stored in the case for one run with `--no-supplement-10-pct`.


## Strict CLI validation

The CLI uses the same public validation rules as the Python/JSON API. Invalid units are not guessed: a JSON value `cut_length_mm: 7` is rejected rather than treated as 7000 mm. `NaN`/`Infinity`, fractional exits/bars/billets, and numeric strings inside JSON are rejected with controlled PX errors.

For annual demand, `--unit bars` requires a whole integer value, for example `--value 300 --unit bars`.
