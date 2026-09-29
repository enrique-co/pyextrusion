# Engineering API

The public analytical interface is available from `pyextrusion.engineering`.
The examples below use only symbols exported by that package in PyExtrusion
0.18.0.

## Mechanical screening chain

```python
from pyextrusion.engineering import (
    AA6063,
    axisymmetric_pressure_breakdown,
    breakthrough_pressure_increment_mpa_from_log_z,
    check_force_capacity,
    flow_stress_mpa,
    log_zener_hollomon_parameter,
    modified_feltham_mean_strain_rate_s_1,
)

ram_speed_mm_s = 0.70
container_diameter_mm = 210.0
extrusion_ratio = 40.0
billet_temperature_c = 470.0

strain_rate = modified_feltham_mean_strain_rate_s_1(
    ram_speed_mm_s,
    container_diameter_mm,
    extrusion_ratio,
)
ln_z = log_zener_hollomon_parameter(
    strain_rate,
    billet_temperature_c,
    AA6063,
)
flow_stress = flow_stress_mpa(
    strain_rate,
    billet_temperature_c,
    AA6063,
)
breakthrough = breakthrough_pressure_increment_mpa_from_log_z(
    ln_z,
    AA6063,
)
pressure = axisymmetric_pressure_breakdown(
    flow_stress_mpa=flow_stress,
    extrusion_ratio=extrusion_ratio,
    friction_factor_m=1.0,
    billet_contact_length_mm=800.0,
    container_diameter_mm=container_diameter_mm,
    breakthrough_increment_mpa=breakthrough,
)

# Semantic name used by the public documentation.
f_baseline_mn = pressure.required_force_mn
screening = check_force_capacity(
    required_force_mn=f_baseline_mn,
    configured_force_limit_mn=35.0,
)
f_reserve_mn = screening.margin_mn

print(f_baseline_mn)
print(f_reserve_mn, screening.within_limit)
```

`required_force_mn` is the API attribute; its engineering interpretation here
is `F_baseline`. Likewise, `margin_mn` is reported publicly as the arithmetic
`F_reserve`. Neither value predicts the final die load or establishes a safety
margin. See [Mechanical baseline](../engineering/mechanical-baseline.md).

## Select AA6060 or AA6063 explicitly

```python
from pyextrusion.engineering import (
    AA6060,
    AA6063,
    flow_stress_mpa,
)

for model in (AA6060, AA6063):
    stress = flow_stress_mpa(
        mean_strain_rate_s_1=0.30,
        temperature_c=470.0,
        model=model,
    )
    print(model.alloy, stress)
```

PyExtrusion never substitutes one alloy dataset for the other.

## Bounded thermal calls

```python
from pyextrusion.engineering import (
    saha_complete_sticking_thermal_source_terms,
    sheppard_billet_container_interface_temperature_c,
    stuwe_surface_exit_temperature_estimate,
)

stuwe = stuwe_surface_exit_temperature_estimate(
    billet_temperature_c=470.0,
    flow_stress_mpa=20.0,
    extrusion_ratio=40.0,
    ram_speed_mm_s=0.70,
    billet_contact_length_mm=800.0,
    exit_speed_m_min=28.0,
    die_land_length_mm=10.0,
)

saha = saha_complete_sticking_thermal_source_terms(
    flow_stress_mpa=20.0,
    mean_strain_rate_s_1=0.30,
    ram_speed_mm_s=0.70,
    exit_speed_m_min=28.0,
)

interface_temperature_c = sheppard_billet_container_interface_temperature_c(
    billet_temperature_c=470.0,
    container_temperature_c=430.0,
)

print(stuwe.estimated_surface_exit_temperature_c)
print(saha.deformation_heat_generation_w_m3)
print(interface_temperature_c)
```

These are three different result types: a limited surface estimate, local
source terms and an interface-temperature relationship. None is a
production-grade exit-temperature predictor. See
[Thermal boundaries](../engineering/thermal-boundaries.md).

## Other public engineering groups

The package also exports typed source metadata, explicit press engineering
configuration, hydraulic identities and power/energy helpers. Inspect
`pyextrusion.engineering.__all__` for the complete supported symbol list.
