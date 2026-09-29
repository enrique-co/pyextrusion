"""Public alloy aliases preserve dataset identity and numerical behavior."""
import pytest

import pyextrusion.engineering as engineering
from pyextrusion.engineering import (
    AA6060,
    AA6060_VERLINDEN_1993,
    AA6063,
    AA6063_SHEPPARD_1999,
    flow_stress_mpa,
)


def test_alloy_aliases_are_the_same_source_traced_objects():
    assert AA6060 is AA6060_VERLINDEN_1993
    assert AA6063 is AA6063_SHEPPARD_1999
    assert AA6060.provenance is AA6060_VERLINDEN_1993.provenance
    assert AA6063.provenance is AA6063_SHEPPARD_1999.provenance
    assert {"AA6060", "AA6063", "AA6060_VERLINDEN_1993", "AA6063_SHEPPARD_1999"} <= set(engineering.__all__)


@pytest.mark.parametrize("alias,source", [(AA6060, AA6060_VERLINDEN_1993), (AA6063, AA6063_SHEPPARD_1999)])
@pytest.mark.parametrize("temperature_c", [450.0, 470.0, 500.0])
@pytest.mark.parametrize("strain_rate_s_1", [0.10, 0.30, 1.0])
def test_alias_flow_stress_is_numerically_identical(alias, source, temperature_c, strain_rate_s_1):
    # These are equivalence checks, not new claims of experimental validity.
    assert flow_stress_mpa(strain_rate_s_1, temperature_c, alias) == flow_stress_mpa(
        strain_rate_s_1, temperature_c, source
    )
