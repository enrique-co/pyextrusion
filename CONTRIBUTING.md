# Contributing to PyExtrusion

Thanks for considering a contribution to PyExtrusion.

PyExtrusion is an engineering calculation library, so changes to numerical behavior, validation rules and public APIs require particular care. Contributions should be reproducible, tested and clearly scoped.

## Development setup

```bash
python -m venv .venv
```

Activate the environment using the command appropriate for your operating system, then install the package and test tools:

```bash
python -m pip install --upgrade pip
python -m pip install -e . pytest
```

Run the test suite:

```bash
python -m pytest -q
```

## Documentation

Install the documentation dependencies:

```bash
python -m pip install -r requirements-docs.txt
```

Build the documentation in strict mode:

```bash
mkdocs build --strict
```

## Contribution guidelines

- Keep engineering calculations deterministic and explicit.
- Do not silently coerce invalid units, types or ambiguous inputs.
- Add or update tests for behavior changes and numerical fixes.
- Update public documentation for user-visible API or calculation changes.
- Preserve backwards compatibility unless a change is intentionally documented as breaking.
- Keep examples generic and free of confidential customer or plant information.
- Do not include private specifications, proprietary documents, customer data or internal production records in issues, pull requests, tests or examples.

## Pull requests

Keep pull requests focused. Explain the engineering problem, the behavior before and after the change, and how the result was validated.

For changes that alter formulas, defaults, thresholds, support boundaries or interpretation of results, maintainers may request additional engineering validation before merging.
