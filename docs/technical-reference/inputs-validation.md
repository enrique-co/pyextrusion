# Inputs & Validation

## Public industrial input limits

The current public model accepts the following supported ranges.

| Input | Supported range |
|---|---|
| Nominal press size | 6–16 in, integer |
| Configurable billet minimum | 100–3000 mm |
| Configurable billet maximum | 100–3000 mm |
| Table length | 10–100 m |
| Cut length | 1000–15000 mm |
| Exit / extrusion speed | 1–100 m/min |
| Technical dead time | 5–30 s |
| Saw kerf | 0 mm, or 3–10 mm |

Additional relational checks apply, for example:

- billet minimum cannot exceed billet maximum;
- cut length cannot exceed the available table length;
- container bore must be larger than the actual billet diameter when both are explicitly supplied;
- exits, explicit cuts, requested bars and requested billets must be whole positive integers.

These ranges define the current supported software domain. They should not be interpreted as universal physical limits of the aluminium extrusion industry.

---


## Numerical behaviour and input validation

PyExtrusion is designed for deterministic software integration.

Public inputs follow these rules:

- numerical values must be finite;
- `NaN`, positive infinity and negative infinity are rejected;
- numeric strings are not silently converted;
- Python booleans are not accepted as substitute integers;
- structural counts such as exits, bars and billets must be integral;
- JSON input is treated strictly;
- predictable input errors are reported through controlled PyExtrusion errors.

This is particularly important when PyExtrusion is used behind a GUI, web service, ERP or MES integration.

---
