# JSON and command line use

PyExtrusion can be used without writing a full Python application.

### Command line identity

```bash
pyextrusion --version
pyextrusion info
```

### Validate an input file

```bash
pyextrusion validate press.json
pyextrusion validate planning_case.json --kind planning
pyextrusion validate production_sequence.json --kind sequence
```

Invalid values return controlled PX error codes.

### Calculate a process or study from the CLI

```bash
pyextrusion calculate case.json --press press.json
```

JSON output:

```bash
pyextrusion calculate case.json --press press.json --format json --pretty
```

### Planning from the CLI

```bash
pyextrusion plan planning_case.json --press press.json --bars 300
pyextrusion plan planning_case.json --press press.json --kg 2500
pyextrusion plan planning_case.json --press press.json --metres 1800
pyextrusion plan planning_case.json --press press.json --billets 20
pyextrusion plan planning_case.json --press press.json --hours 2
```

### Production sequence from the CLI

```bash
pyextrusion sequence production_sequence.json
pyextrusion sequence production_sequence.json --format json --pretty
```

### Compare presses from the CLI

Process:

```bash
pyextrusion compare-process planning_case.json press_a.json press_b.json press_c.json
```

Planning:

```bash
pyextrusion compare-planning planning_case.json press_a.json press_b.json --bars 300
```

Sequence:

```bash
pyextrusion compare-sequence production_sequence.json press_a.json press_b.json press_c.json
```

### JSON input is strict

PyExtrusion intentionally rejects ambiguous or unsafe input forms.

Examples that are rejected:

```json
{"exits": 2.5}
```

```json
{"exits": true}
```

```json
{"cut_length_mm": "7000"}
```

```json
{"cut_length_mm": 7}
```

The last example is rejected because `7` means 7 mm; PyExtrusion does not guess that the user intended 7 m.

Non-finite values such as `NaN` and `Infinity` are also rejected.

### Discover result fields

```bash
pyextrusion fields
pyextrusion fields --section scrap
pyextrusion field production.bars_manufactured
```

### Discover error codes

```bash
pyextrusion errors
pyextrusion error PX1003
```

These commands are useful for software integrations because they expose the public identifiers instead of relying on guessed field names.

---
