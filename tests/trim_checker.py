"""Independent physical ledger. Deliberately imports NO PyExtrusion code."""
import math


def reconstruct(*, billets, cuts, sequential_pulls, groups, cut_m, trim_total,
                final_kerf, puller_kerf, linear_mass, speed, dead_seconds,
                density, billet_diameter_mm, container_diameter_mm, butt_mm,
                billet_saw_mm, mass_coefficient_override=None):
    assert sequential_pulls in (1, 2)
    assert sum(groups) == billets * sequential_pulls
    if sequential_pulls == 2:
        assert all(k == 1 for k in groups)
    assert all(type(k) is int and k > 0 for k in groups)
    per_contribution = trim_total / sequential_pulls
    pieces = []
    for pull, k in enumerate(groups):
        for billet in range(k):
            pieces.append((pull, 'trim', per_contribution / 2))
            if per_contribution > 0:
                pieces.append((pull, 'final', final_kerf))
            for _ in range(cuts):
                pieces.append((pull, 'good', cut_m))
                pieces.append((pull, 'final', final_kerf))
            pieces.append((pull, 'trim', per_contribution / 2))
            if billet < k - 1:
                pieces.append((pull, 'transition', 0.0))
        if per_contribution == 0:
            pieces.append((pull, 'final', final_kerf))  # retained end allowance
        pieces.append((pull, 'puller', puller_kerf))
    length = lambda kind: math.fsum(v for _, name, v in pieces if name == kind)
    count = lambda kind: sum(name == kind for _, name, _ in pieces)
    cb = mass_coefficient_override or density * math.pi * billet_diameter_mm**2 / 4 / 1e9
    butt_mass = density * math.pi * container_diameter_mm**2 / 4 * butt_mm / 1e9
    through_length = math.fsum(v for _, _, v in pieces)
    good = length('good') * linear_mass
    dead_events = max(billets - 1, 0) + (billets if sequential_pulls == 2 else 0)
    total_min = through_length / speed + dead_events * dead_seconds / 60
    return dict(
        final_saw_events=count('final'), internal_transitions=count('transition'),
        puller_saw_events=count('puller'), billet_saw_events=billets,
        final_kerf_order_m=length('final'), final_saw_kg=length('final')*linear_mass,
        front_scrap_kg=length('trim')*linear_mass, puller_saw_kg=length('puller')*linear_mass,
        butt_kg=billets*butt_mass, billet_saw_kg=billets*billet_saw_mm*cb,
        physical_loss_kg=(length('trim')+length('final')+length('puller'))*linear_mass
            + billets*(butt_mass+billet_saw_mm*cb),
        through_die_kg=through_length*linear_mass, physical_extruded_order_m=through_length,
        good_kg=good, dead_time_events=dead_events, dead_time_min=dead_events*dead_seconds/60,
        extrusion_min=through_length/speed, total_min=total_min, total_hours=total_min/60,
        net_kg_h=good*60/total_min,
    )
