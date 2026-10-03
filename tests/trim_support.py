"""Synthetic public scenarios and engine adapters, independent of plant records."""
from pyextrusion import Press, SawSpec, Profile, Production, StudyCase, migrate_legacy_trim
from trim_checker import reconstruct

SCENARIOS = tuple(f'{family}_{variant}' for family in ('single','paired','triple','split') for variant in range(4))


def scenario(sid, canonical=True):
    family, _, variant = sid.partition('_')
    variant = int(variant or 0)
    sequential = family == 'split'
    press = Press(name='Synthetic '+sid, nominal_size_in=8,
        billet_diameter_mm=190, container_diameter_mm=200,
        billet_min_length_mm=450, billet_max_length_mm=1400,
        table_length_m={'single':17,'paired':32,'triple':47,'split':17}[family],
        density_kg_m3=2700, saws=SawSpec(7,3,4), dead_time_sec=18)
    total = 1.2 + variant * .2
    case = StudyCase(Profile(1.5 if sequential else 2.5, 1 if sequential else 2, 'solid'),
        Production(18+variant*3,4000,25,cuts=3,butt_mm=25,
            front_scrap_m=total/2 if sequential else total))
    if canonical:
        case = migrate_legacy_trim(case, profiles_per_billet=2 if sequential else 1)
    return press, case


def metrics(r):
    return dict(final_saw_events=r.production.final_saw_events,
        internal_transitions=r.production.internal_billet_transitions,
        puller_saw_events=r.production.puller_saw_events,
        billet_saw_events=r.production.billet_saw_events,
        final_saw_kg=r.scrap.final_saw_kg, front_scrap_kg=r.scrap.front_scrap_kg,
        puller_saw_kg=r.scrap.puller_saw_kg, butt_kg=r.scrap.butt_kg,
        billet_saw_kg=r.scrap.billet_saw_kg, physical_loss_kg=r.fixed_scrap_kg,
        loss_good_pct=r.fixed_scrap_pct, through_die_kg=r.productivity.extruded_total_kg,
        physical_extruded_order_m=r.extrusion_time_total_min*r.exit_speed_m_min,
        full_pull_m=r.table_occupancy_length_m, billet_length_mm=r.billet_length_mm,
        recommended_billet_mm=r.recommended_billet_length_mm, good_kg=r.good_kg_manufactured,
        billets=r.billets, pulls=r.n_pulls, bars=r.bars_manufactured,
        bars_per_billet=r.bars_per_billet, dead_time_events=r.dead_time_events,
        dead_time_min=r.dead_time_total_min, extrusion_min=r.extrusion_time_total_min,
        total_min=r.total_time_min, total_hours=r.timing.total_hours,
        net_kg_h=r.real_net_kg_h, extrusion_ratio=r.extrusion_ratio,
        ram_speed_mm_s=r.ram_speed_mm_s, exit_speed_m_min=r.exit_speed_m_min)


def independent(press, case, r):
    p = r.profiles_per_billet
    groups = ([r.billets_per_pull]*r.full_pulls + ([r.remaining_billets] if r.remaining_billets else [])) if p == 1 else [1]*(2*r.billets)
    q = case.production
    trim = q.trim_total_per_billet_m
    if trim is None:
        trim = r.process.applied_front_scrap_m*p
    values = reconstruct(billets=r.billets, cuts=r.cuts, sequential_pulls=p, groups=groups,
        cut_m=q.cut_length_mm/1000, trim_total=trim, final_kerf=press.saws.final_mm/1000,
        puller_kerf=press.saws.puller_mm/1000,
        linear_mass=case.profile.exits*case.profile.linear_weight_kg_m,
        speed=r.exit_speed_m_min, dead_seconds=press.dead_time_sec,
        density=press.density_kg_m3, billet_diameter_mm=press.billet_diameter_mm,
        container_diameter_mm=press.container_diameter_mm, butt_mm=r.butt_mm,
        billet_saw_mm=press.saws.billet_mm, mass_coefficient_override=press.billet_kg_per_mm_override)
    return groups, values
