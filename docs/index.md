# PyExtrusion 0.18.0

**Deterministic engineering calculations for aluminium extrusion**

PyExtrusion 0.18.0 brings production planning, bounded analytical engineering
models and deterministic production economics together in one Python package.

!!! info "0.18.0 release candidate — publication pending"
    ```bash
    pip install pyextrusion
    ```

    This command installs the published package, not necessarily this candidate.
    To validate **0.18.0** before publication, use the candidate source or local wheel.
    See the
    [PyPI project page](https://pypi.org/project/pyextrusion/) or
    [source repository](https://github.com/enrique-co/pyextrusion).

## Three working areas

<div class="grid cards" markdown>

-   **Production & Planning**

    ---

    Billet sizing, extrusion geometry, productivity, multi-billet processes,
    operational planning, production sequences and multi-press comparison.

    [Start with the User Guide](user-guide/index.md)

-   **Engineering**

    ---

    Source-traced AA6063 and AA6060 constitutive models, modified Feltham mean
    strain rate, Zener-Hollomon, steady-state flow stress, Sheppard
    axisymmetric pressure and bounded mechanical and thermal analytical tools.

    [Explore Engineering](engineering/index.md)

-   **Economics**

    ---

    Deterministic production cost, material and scrap economics,
    tooling/development costs and sales-margin calculations from explicit
    caller-supplied assumptions.

    [Calculate basic economics](user-guide/basic-economics.md)

</div>

## Model boundaries matter

In 0.18.0, `butt_mm` is physical residual thickness in the container. Butt mass uses the container section and is converted once to incoming-billet equivalent length. Existing physical values and the measured incoming-billet coefficient remain supported. See [physical butt geometry](technical-reference/geometry.md#physical-butt-and-equivalent-incoming-billet-length).

The Engineering pressure/force result is an **equivalent-axisymmetric
mechanical baseline**, not the final load prediction for a shaped, bridge or
porthole die. Thermal functions are bounded analytical estimates and local
source terms; PyExtrusion does not currently provide a production-grade
exit-temperature predictor.

Read the [model boundaries](user-guide/model-boundaries.md) before using these
results in an industrial decision.

## Documentation routes

- **User Guide** — install the package and complete practical workflows.
- **Engineering** — understand the public models and their limits.
- **Technical Reference** — review production formulas, units and semantics.
- **API Reference** — integrate public Python, JSON and CLI interfaces.
- **Examples** — use complete practical patterns.

PyExtrusion supports engineering judgement. It does not replace press, die,
alloy or plant-specific expertise.
