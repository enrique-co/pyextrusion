# Error catalog

PyExtrusion exposes stable **PX error codes**. These identify public input/configuration/result errors independently from operating-system CLI exit codes.

List all documented errors:

```bash
pyextrusion errors
```

Describe one code:

```bash
pyextrusion error PX1004
```

## Catalog

| Code | Name | Category | Description | Typical resolution | CLI exit |
|---|---|---|---|---|---:|
| `PX1001` | `InvalidPressConfiguration` | configuration | The press configuration is missing required values or contains invalid values. | Review the press JSON or PressSpec values and run `pyextrusion validate press.json`. | 2 |
| `PX1002` | `InvalidProfileInput` | input | The profile definition is missing required values or contains invalid values. | Provide profile_type explicitly using solid, plate, hollow or tubular; also review linear weight, exits and optional section values. | 2 |
| `PX1003` | `InvalidProductionInput` | input | The production definition is missing required values or contains invalid values. | Review speed, cut length, requested bars, scrap, cuts and manual overrides. | 2 |
| `PX1004` | `UnknownResultField` | result | A requested result field path does not exist in the public result-field catalog. | Run `pyextrusion fields` or `pyextrusion field <path>` and use an exact documented field path. | 2 |
| `PX1005` | `UnsupportedSchemaVersion` | schema | The JSON schema_version is not supported by this PyExtrusion release. | Use a supported schema version or migrate the file before loading it. | 2 |
| `PX1006` | `InvalidAnnualDemand` | input | The annual-demand definition is invalid. | Use unit kg, m or bars and provide a value greater than zero. | 2 |
| `PX1007` | `InputFileError` | file | An input file cannot be read, is not valid JSON, or has an invalid top-level structure. | Check the path and JSON syntax, then validate the file again. | 2 |
| `PX1008` | `UnknownResultSection` | result | A requested structured result section does not exist. | Use one of geometry, billet, production, scrap, productivity, timing or process. | 2 |
| `PX1009` | `InvalidResultSelection` | result | A result selection request is empty or malformed. | Provide at least one exact documented result field path. | 2 |
| `PX1010` | `InvalidStudyAdjustment` | input | A requested StudyCase adjustment uses an unknown or unsupported field name. | Use `with_profile()`, `with_production()` or `replace()` with documented StudyCase input fields. | 2 |
| `PX1011` | `InvalidPlanningRequest` | input | The operational planning request is invalid. | Use bars, kg, m, billets, minutes or hours with a positive value; bars and billets must be whole numbers. | 2 |
| `PX1012` | `InvalidProductionSequence` | input | A production-sequence definition is invalid. | Provide at least one `ProductionOrder` using a `PlanningCase` and a bars, kg, m or billets request; no external plant times are inferred. | 2 |
| `PX1013` | `InvalidComparison` | input | A multi-press comparison request is invalid. | Provide at least two presses and a supported process, planning or sequence comparison input. | 2 |

## Python exceptions

```python
from pyextrusion import PyExtrusionError

try:
    result.value("scrap.foo")
except PyExtrusionError as exc:
    print(exc.code)
    print(exc.name)
    print(exc.message)
```

## CLI exit codes

- `0` — command completed successfully.
- `2` — documented user input, configuration, schema, field-selection or validation error.

The **PX code** carries the specific error meaning; the CLI exit code is intentionally broader for shell/script integration.