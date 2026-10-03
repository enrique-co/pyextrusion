import json
import math
import sys
from dataclasses import replace

import pytest

from pyextrusion import (
    Production, Process, StudyCase, PlanningCase, PlanningRequest, SawSpec,
    calculate_case, calculate_process, calculate_planning, calculate_simple,
    migrate_legacy_trim, case_from_dict, planning_case_from_dict,
    save_case_json, save_press_json, load_case_json, format_result,
    InvalidProductionInputError, ProductionOrder, calculate_production_sequence,
    validate_case, validate_planning_case,
)
from trim_support import SCENARIOS, scenario, metrics, independent

@pytest.mark.parametrize('sid', SCENARIOS)
def test_independent_ledger_for_all_16_scenarios(sid):
    press, case = scenario(sid)
    r = calculate_case(press, case)
    assert r.viable and r.supported
    _, check = independent(press, case, r)
    actual = metrics(r)
    actual['final_kerf_order_m'] = r.production.final_saw_events*press.saws.final_mm/1000
    for key, value in check.items():
        assert actual[key] == pytest.approx(value, rel=2e-12, abs=1e-9), key


@pytest.mark.parametrize('sid', SCENARIOS)
def test_synthetic_legacy_migration_preserves_selected_physics(sid):
    canonical = calculate_case(*scenario(sid))
    legacy = calculate_case(*scenario(sid, canonical=False))
    assert metrics(canonical) == metrics(legacy)


@pytest.mark.parametrize('sid', ['single','paired','triple'])
def test_synthetic_closed_form_billet_length(sid):
    press, case = scenario(sid)
    r = calculate_case(press, case)
    # Hand-constructed synthetic block: three 4 m bars and 1.2 m total trim.
    k = {'single':1,'paired':2,'triple':3}[sid]
    assert r.billets_per_pull == k
    block = 3*4 + 1.2 + 4*.004 + .003/k
    cb = 2700*math.pi*190**2/4/1e9
    butt = 2700*math.pi*200**2/4*25/1e9
    assert r.billet_length_mm == pytest.approx((block*5+butt)/cb, rel=2e-12)


@pytest.mark.parametrize('sid,bars,groups,final_events', [
    ('single',6,[1],4), ('paired',12,[2],8), ('triple',18,[3],12),
    ('paired',13,[2,1],12), ('paired',7,[2],8),
    ('triple',19,[3,1],16), ('triple',7,[2],8), ('triple',1,[1],4),
])
def test_actual_full_and_partial_groups(sid, bars, groups, final_events):
    press, case = scenario(sid)
    case = replace(case, production=replace(case.production, bars_requested=bars))
    r = calculate_case(press, case)
    actual_groups, check = independent(press, case, r)
    assert actual_groups == groups
    assert r.production.final_saw_events == check['final_saw_events'] == final_events
    assert r.production.internal_billet_transitions == sum(k-1 for k in groups)
    assert r.dead_time_events == r.billets-1
    assert r.production.puller_saw_events == len(groups)
    assert r.production.billet_saw_events == sum(groups)
    for key, value in check.items():
        if key != 'final_kerf_order_m':
            assert metrics(r)[key] == pytest.approx(value, rel=2e-12, abs=1e-9)


@pytest.mark.parametrize('sid', ['paired', 'triple'])
def test_full_pull_matches_synthetic_longitudinal_pieces(sid):
    r = calculate_case(*scenario(sid))
    k = 2 if sid == 'paired' else 3
    # A literal piece ledger independent of the calculation engine.
    pieces = [.6,.004,4,.004,4,.004,4,.004,.6]*k + [.003]
    assert r.table_occupancy_length_m == pytest.approx(math.fsum(pieces), abs=1e-12)
    cfg = next(c for c in r.configurations if c.name == r.recommended_configuration)
    assert cfg.final_saw_events_per_pull == k*4
    assert cfg.internal_billet_transitions_per_pull == k-1


@pytest.mark.parametrize('sid', ['paired', 'triple', 'split'])
def test_zero_final_kerf_keeps_physical_event_counts(sid):
    press, case = scenario(sid)
    press = replace(press, saws=replace(press.saws, final_mm=0))
    r = calculate_case(press, case)
    assert r.production.final_saw_events == r.billets*r.profiles_per_billet*(r.cuts+1)
    assert r.scrap.final_saw_kg == 0
    _, check = independent(press, case, r)
    assert r.real_net_kg_h == pytest.approx(check['net_kg_h'], rel=2e-12)


@pytest.mark.parametrize('sid', ['paired', 'triple', 'split'])
def test_zero_trim_retains_one_end_allowance_per_actual_pull(sid):
    press, case = scenario(sid)
    case = replace(case, production=replace(case.production, trim_total_per_billet_m=0))
    r = calculate_case(press, case)
    assert r.viable
    assert r.process.trim_topology == 'zero_trim_end_allowance'
    assert r.production.final_saw_events == r.billets*r.profiles_per_billet*r.cuts+r.n_pulls
    assert r.scrap.front_scrap_kg == 0
    _, check = independent(press, case, r)
    assert r.fixed_scrap_kg == pytest.approx(check['physical_loss_kg'])


def test_synthetic_split_explicit_legacy_migration_roundtrip_and_invariant():
    press, legacy = scenario('split', canonical=False)
    original = calculate_case(press, legacy)
    canonical = migrate_legacy_trim(legacy, profiles_per_billet=2)
    assert legacy.production.front_scrap_m == .6
    assert canonical.production.front_scrap_m is None
    assert canonical.production.trim_total_per_billet_m == 1.2
    saved = json.loads(json.dumps(canonical.to_dict()))
    loaded = case_from_dict(saved)
    migrated = calculate_case(press, loaded)
    assert metrics(migrated) == metrics(original)
    assert migrated.process.trim_total_per_billet_m == 1.2
    assert migrated.process.trim_per_pull_m == .6
    assert migrated.process.trim_input_semantics == 'canonical_total_per_incoming_billet'
    assert 'Legacy front_scrap_m' in ' '.join(original.warnings)
    assert migrated.profiles_per_billet == 2
    assert migrated.bars_per_pull == 3 and migrated.bars_per_billet == 6
    assert migrated.good_kg_manufactured/migrated.billets == pytest.approx(36)


@pytest.mark.parametrize('total', [-1, True, '2', float('nan'), float('inf'), -float('inf')])
@pytest.mark.parametrize('factory', [Production, Process])
def test_canonical_trim_strict_validation(total, factory):
    args = (24,7000,10) if factory is Production else (24,7000)
    with pytest.raises(InvalidProductionInputError):
        factory(*args, trim_total_per_billet_m=total)


@pytest.mark.parametrize('legacy', ['front_scrap_m','multi_billet_front_scrap_m'])
@pytest.mark.parametrize('value', [0, 2.5])
@pytest.mark.parametrize('factory', [Production, Process])
def test_dual_input_is_controlled_ambiguity_even_legacy_zero(legacy, value, factory):
    args = (24,7000,10) if factory is Production else (24,7000)
    with pytest.raises(InvalidProductionInputError, match='cannot be combined'):
        factory(*args, trim_total_per_billet_m=5, **{legacy:value})


@pytest.mark.parametrize('p', [0,3,True,2.0,'2'])
def test_migration_requires_known_supported_family(p):
    _, case = scenario('split', canonical=False)
    with pytest.raises(InvalidProductionInputError):
        migrate_legacy_trim(case, profiles_per_billet=p)


def test_migration_legacy_override_requires_explicit_choice():
    _, case = scenario('paired', canonical=False)
    case = replace(case, production=replace(case.production, multi_billet_front_scrap_m=1))
    with pytest.raises(InvalidProductionInputError):
        migrate_legacy_trim(case, profiles_per_billet=1)
    assert migrate_legacy_trim(case, profiles_per_billet=1, use_multi_billet_override=True).production.trim_total_per_billet_m == 1
    assert migrate_legacy_trim(case, profiles_per_billet=1, use_multi_billet_override=False).production.trim_total_per_billet_m == 1.2
    with pytest.raises(InvalidProductionInputError):
        migrate_legacy_trim(case, profiles_per_billet=2, use_multi_billet_override=True)
    canonical = migrate_legacy_trim(case, profiles_per_billet=1, use_multi_billet_override=False)
    with pytest.raises(InvalidProductionInputError):
        migrate_legacy_trim(canonical, profiles_per_billet=1)


@pytest.mark.parametrize('limit,offset', [('table',-1e-7),('table',1e-7),('max',-1e-7),('max',1e-7),('min',-1e-7),('min',1e-7)])
def test_multibillet_unrounded_feasibility(limit, offset):
    press, case = scenario('paired')
    ref = calculate_case(press,case)
    if limit == 'table':
        p = replace(press, table_length_m=ref.table_occupancy_length_m+offset)
        r = calculate_case(p,case)
        assert r.billets_per_pull == (1 if offset < 0 else 2)
    else:
        p = replace(press, **{f'billet_{limit}_length_mm':ref.billet_length_mm+offset})
        r = calculate_case(p,case)
        cfg = next(c for c in r.configurations if c.profiles_per_billet == 1)
        assert cfg.valid is ((offset > 0) if limit == 'max' else (offset < 0))


def test_canonical_json_cli_api_planning_sequence_and_reporting(tmp_path, monkeypatch, capsys):
    press, case = scenario('split')
    cp, pp = tmp_path/'case.json', tmp_path/'press.json'
    save_case_json(case,cp); save_press_json(press,pp)
    assert load_case_json(cp) == case
    assert not validate_case(case)
    pc = case.to_planning_case()
    assert not validate_planning_case(pc)
    pc2 = planning_case_from_dict(json.loads(json.dumps(pc.to_dict())))
    process = calculate_process(press, pc2)
    assert process.trim_total_per_billet_m == 1.2 and process.trim_per_pull_m == .6
    plan = calculate_planning(press,pc2,PlanningRequest.billets(3))
    assert plan.calculation.production.final_saw_events == 24
    seq = calculate_production_sequence(press,[ProductionOrder('split',pc2,PlanningRequest.billets(3))])
    assert seq.total_fixed_scrap_kg == plan.calculation.fixed_scrap_kg
    from pyextrusion.cli import main
    monkeypatch.setattr(sys,'argv',['pyextrusion','calculate',str(cp),'--press',str(pp),'--field','process.trim_total_per_billet_m'])
    main()
    assert float(capsys.readouterr().out) == 1.2
    report = format_result(calculate_case(press,case))
    assert 'Final saw events' in report and 'Commercial cuts' in report and 'Total trim / billet' in report
    direct = calculate_simple(press, linear_weight_kg_m=1.5, exits=1, profile_type='solid',
        exit_speed_m_min=18, cut_length_mm=4000, bars_requested=3, cuts=3, butt_mm=25,
        trim_total_per_billet_m=1.2)
    assert direct.process.trim_per_pull_m == .6


def test_total_trim_larger_than_table_can_fit_after_sequential_distribution():
    from pyextrusion import Press, Profile, validate_study
    p = Press(name='Split trim',nominal_size_in=8,table_length_m=10,
              billet_min_length_mm=500,billet_max_length_mm=1200)
    c = StudyCase(Profile(5,1,'solid'),Production(20,1000,2,cuts=1,trim_total_per_billet_m=12))
    assert not [m for m in validate_study(c.to_study_input(p)) if m.level == 'error']
    r = calculate_case(p,c)
    assert r.viable and r.profiles_per_billet == 2
    assert r.process.trim_total_per_billet_m == 12
    assert r.process.trim_per_pull_m == 6
    assert r.scrap.front_scrap_kg == 12*5


def test_canonical_three_pull_requirement_remains_controlled_unsupported():
    from pyextrusion import Press, Profile
    p = Press(name='Unsupported split',nominal_size_in=8,table_length_m=10)
    cb = p.density_kg_m3*math.pi*p.billet_diameter_mm**2/4/1e9
    mb = p.density_kg_m3*math.pi*p.container_diameter_mm**2/4*35/1e9
    length = (2*(3*(7+.005+2*.005)+6)+mb)/cb
    p = replace(p,billet_min_length_mm=length-1e-7,billet_max_length_mm=length+1e-7)
    c = StudyCase(Profile(2,1,'solid'),Production(24,7000,3,cuts=1,butt_mm=35,trim_total_per_billet_m=6))
    r = calculate_case(p,c)
    assert not r.supported and not r.viable
    assert r.required_profiles_per_billet == 3
    assert r.process.trim_total_per_billet_m == 6
    assert r.process.trim_topology == 'unresolved'
    assert r.production.final_saw_events == 0


def test_low_level_input_cannot_bypass_trim_ambiguity_validation():
    from pyextrusion import calculate
    p,c = scenario('split')
    bad = replace(c.to_study_input(p),front_scrap_m=0)
    with pytest.raises(InvalidProductionInputError,match='cannot be combined'):
        calculate(bad)


def test_quantity_free_migration_retains_canonical_trace():
    p,c = scenario('split',canonical=False)
    migrated = migrate_legacy_trim(c.to_planning_case(),profiles_per_billet=2)
    assert migrated.process.trim_total_per_billet_m == 1.2
    assert calculate_process(p,migrated).trim_per_pull_m == .6
