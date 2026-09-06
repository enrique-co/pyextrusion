"""Minimal PyExtrusion 0.16.0 / calculation-model v2.4 example."""
from pyextrusion import Press, calculate_simple

# Only the nominal press size and run-out table are supplied here.
# PyExtrusion resolves billet/container geometry, billet limits, dead time,
# saw kerfs and target productivity from documented defaults.
press = Press(
    name="My 8-inch press",
    nominal_size_in=8,
    table_length_m=54,
)

result = calculate_simple(
    press,
    linear_weight_kg_m=1.35,
    exits=2,
    profile_type="solid",
    exit_speed_m_min=24,
    cut_length_mm=7000,
    bars_requested=1000,
    front_scrap_m=2,
)

print(f"Viable: {result.viable}")
print(f"Container: {press.container_diameter_mm:.3f} mm ({press.container_diameter_source})")
print(f"RE: {result.extrusion_ratio:.2f}:1 [{result.extrusion_ratio_status}]")
print(f"Calculated billet: {result.billet_length_mm:.2f} mm")
print(f"Recommended billet: {result.recommended_billet_length_mm} mm")
print(f"Net productivity: {result.real_net_kg_h:.0f} kg/h")
print(f"Productivity index: {result.productivity_index:.1f}/100")
