"""Synthetic two-pull legacy migration; prints results without modifying input files."""
from pyextrusion import (
    Press, SawSpec, Profile, Production, StudyCase,
    calculate_case, migrate_legacy_trim,
)

press = Press(name="Synthetic split", nominal_size_in=8, billet_diameter_mm=190,
    container_diameter_mm=200, billet_min_length_mm=450, billet_max_length_mm=1400,
    table_length_m=17, saws=SawSpec(7,3,4), dead_time_sec=18)
legacy = StudyCase(Profile(1.5,1,"solid"),
    Production(18,4000,25,front_scrap_m=.6,cuts=3,butt_mm=25))
canonical = migrate_legacy_trim(legacy, profiles_per_billet=2)
before, after = (calculate_case(press,c) for c in (legacy,canonical))
assert before.billet_length_mm == after.billet_length_mm
assert before.real_net_kg_h == after.real_net_kg_h
assert before.fixed_scrap_kg == after.fixed_scrap_kg
assert after.process.trim_total_per_billet_m == 1.2
assert after.process.trim_per_pull_m == .6
print(canonical.to_dict())
print(after.production.to_dict() if hasattr(after.production,"to_dict") else after.production)
