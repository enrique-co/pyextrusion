# Errors and troubleshooting

PyExtrusion uses stable public error codes beginning with `PX`.

### Common error categories

| Code | Name | Typical meaning |
|---|---|---|
| PX1001 | InvalidPressConfiguration | Invalid press definition or range |
| PX1002 | InvalidProfileInput | Invalid profile data |
| PX1003 | InvalidProductionInput | Invalid process/production data |
| PX1004 | UnknownResultField | Unknown result-field identifier |
| PX1005 | UnsupportedSchemaVersion | JSON schema version is not supported |
| PX1006 | InvalidAnnualDemand | Invalid annual-demand input |
| PX1007 | InputFileError | Input file cannot be read/parsed correctly |
| PX1008 | UnknownResultSection | Unknown result section |
| PX1009 | InvalidResultSelection | Invalid field/result selection |
| PX1010 | InvalidStudyAdjustment | Invalid case adjustment |
| PX1011 | InvalidPlanningRequest | Invalid planning request |
| PX1012 | InvalidProductionSequence | Invalid production sequence |
| PX1013 | InvalidComparison | Invalid multi-press comparison |

### Example: wrong unit

Input:

```python
Process(
    exit_speed_m_min=24,
    cut_length_mm=7,
)
```

PyExtrusion rejects the cut length because the public field is in millimetres and the supported range starts at 1000 mm.

Correct:

```python
cut_length_mm=7000
```

### Example: fractional exits

Invalid:

```python
Profile(
    linear_weight_kg_m=1.35,
    exits=2.5,
    profile_type="solid",
)
```

The number of exits must be a whole positive integer.

### Example: numeric string in JSON

Invalid:

```json
{"cut_length_mm": "7000"}
```

Correct:

```json
{"cut_length_mm": 7000}
```

PyExtrusion does not silently convert numeric strings.

### Example: sequence contains a time-window order

A sequence represents explicit production orders. Requests such as `PlanningRequest.hours(2)` are capacity questions and should be calculated independently, not used as a normal `ProductionOrder` quantity.

### Example: unsupported but not necessarily impossible in the real world

If PyExtrusion says a scenario is `supported=False`, it means the current model is not approved to calculate that configuration. It does **not** necessarily mean the physical process is impossible in every extrusion plant.

### CLI help

Use:

```bash
pyextrusion errors
```

or:

```bash
pyextrusion error PX1011
```

for the package's current error descriptions.

---
