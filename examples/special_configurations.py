"""Inspect the configuration candidates evaluated by the v2.1 billet-first engine."""
from pyextrusion import Press, calculate_simple

press = Press(
    name="Special-configuration demo",
    nominal_size_in=8,
    table_length_m=54,
)

result = calculate_simple(
    press,
    linear_weight_kg_m=5.0,
    exits=1,
    profile_type="solid",
    exit_speed_m_min=15,
    cut_length_mm=7000,
    bars_requested=100,
    front_scrap_m=2,
)

print("Recommended:", result.recommended_configuration)
for cfg in result.configurations:
    print(
        cfg.name,
        "valid=" + str(cfg.valid),
        "billet_mm=" + f"{cfg.billet_length_mm:.1f}",
        "table_m=" + f"{cfg.table_occupancy_length_m:.1f}",
        "reasons=" + str(cfg.reasons),
    )
