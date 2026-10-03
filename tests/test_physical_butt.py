"""Physical butt expectations are constructed from pi/rho/diameters, not core helpers."""
import json
import math
import sys
from dataclasses import replace

import pytest

from pyextrusion import (
    Press, SawSpec, Profile, Production, Process, StudyCase, PlanningCase, PlanningRequest,
    calculate_case, calculate_process, calculate_planning, compare_presses, compare_processes,
    calculate_annual_demand, AnnualDemandSpec, ProductionOrder, calculate_production_sequence,
    press_from_dict, case_from_dict, save_press_json, save_case_json, format_result,
)
from pyextrusion.engineering import upset_billet_length_mm, aa6063_direct_extrusion_operation_estimate
from pyextrusion.economics.basic import BasicCostSpec, EconomicProductionBasis, calculate_basic_economics


def press_a(**changes):
    kwargs = dict(name="Synthetic butt A", nominal_size_in=8, billet_diameter_mm=190,
                  container_diameter_mm=200, billet_min_length_mm=450, billet_max_length_mm=1400,
                  table_length_m=35, density_kg_m3=2700, saws=SawSpec(7, 3, 4), dead_time_sec=18)
    return Press(**(kwargs | changes))


def press_b(**changes):
    return press_a(**(dict(name="Synthetic butt B", nominal_size_in=9, billet_diameter_mm=216,
        container_diameter_mm=225, billet_min_length_mm=300, billet_max_length_mm=1400,
        table_length_m=38, saws=SawSpec(7, 3, 4), dead_time_sec=18) | changes))


def case_a(butt=15, bars=240):
    return StudyCase(Profile(1.1, 2, "solid"),
        Production(21, 6000, bars, front_scrap_m=1.3, cuts=5, butt_mm=butt))


def raw_coefficients(p):
    return tuple(p.density_kg_m3 * math.pi * d*d / 4 / 1e9
                 for d in (p.billet_diameter_mm, p.container_diameter_mm))


@pytest.mark.parametrize("factory", [press_a, press_b])
@pytest.mark.parametrize("butt", [0, 15, 35])
@pytest.mark.parametrize("override", [None, .095])
def test_butt_mass_equivalence_and_incoming_saw_are_distinct(factory, butt, override):
    p = factory(billet_kg_per_mm_override=override)
    case = case_a(butt)
    r = calculate_case(p, case)
    geometric_cb, cc = raw_coefficients(p)
    cb = override or geometric_cb
    mb = cc * butt
    assert r.viable
    assert r.butt_mm == butt
    assert r.billet.butt_mass_kg == pytest.approx(mb, rel=2e-12)
    assert r.billet.butt_equivalent_billet_mm == pytest.approx(mb/cb, rel=2e-12)
    through_die = case.profile.linear_weight_kg_m * case.profile.exits * r.extruded_length_per_billet_m
    assert r.billet_length_mm == pytest.approx((through_die + mb)/cb, rel=2e-12)
    assert cb * r.billet_length_mm == pytest.approx(through_die + mb, rel=2e-12)
    assert r.scrap.butt_kg == pytest.approx(r.billets*mb, rel=2e-12)
    assert r.scrap.billet_saw_kg == pytest.approx(r.billets*p.saws.billet_mm*cb, rel=2e-12)
    assert r.billet.mass_coefficient_source == ('geometric' if override is None else 'user_plant_override')
    if override is None:
        upset = upset_billet_length_mm(p.billet_diameter_mm, r.billet_length_mm, p.container_diameter_mm)
        assert upset == pytest.approx(through_die/cc + butt, rel=2e-12)
    if butt == 0:
        assert r.billet_length_mm == r.billet_useful_length_mm
        assert r.scrap.butt_kg == 0


@pytest.mark.parametrize("diameter", [190, 216])
def test_equal_diameter_mathematical_limit(diameter):
    # Press validation intentionally requires DC > DB. Test the limiting
    # physical conversion without broadening that pre-existing API contract.
    from pyextrusion.core import _butt_geometry, _billet_lengths
    rho, butt, extruded = 2700, 20, 80
    area = math.pi * (diameter/1000)**2 / 4
    cb = rho * area / 1000
    mass, equivalent = _butt_geometry(rho, area, butt, cb)
    assert mass == pytest.approx(rho*math.pi*diameter**2/4*butt/1e9, rel=2e-12)
    assert equivalent == pytest.approx(butt, rel=2e-12)
    _, length = _billet_lengths(extruded, 1, cb, equivalent)
    assert length == pytest.approx(extruded/cb + butt, rel=2e-12)


@pytest.mark.parametrize("kind,bars,expected_k,expected_p,expected_remaining", [
    ('single', 6, 1, 1, 0), ('paired', 12, 2, 1, 0), ('paired', 13, 2, 1, 1),
    ('triple', 18, 3, 1, 0), ('triple', 19, 3, 1, 1), ('split', 25, 1, 2, 0),
])
def test_one_butt_per_billet_all_families_and_partial_pull(kind, bars, expected_k, expected_p, expected_remaining):
    from trim_support import scenario
    p, case = scenario(kind, canonical=False)
    case = replace(case, production=replace(case.production, bars_requested=bars))
    r = calculate_case(p, case)
    assert (r.billets_per_pull, r.profiles_per_billet, r.remaining_billets) == (expected_k, expected_p, expected_remaining)
    q, prof = case.production, case.profile
    cb, cc = raw_coefficients(p)
    w = prof.linear_weight_kg_m * prof.exits
    cuts = q.cuts
    per_billet = expected_p * (cuts*q.cut_length_mm/1000 + q.front_scrap_m + (cuts+1)*p.saws.final_mm/1000
                    + p.saws.puller_mm/1000/expected_k)
    assert r.billet_length_mm == pytest.approx((w*per_billet+cc*q.butt_mm)/cb, rel=2e-12)
    assert r.scrap.butt_kg == pytest.approx(r.billets*cc*q.butt_mm, rel=2e-12)
    pulls = math.ceil(r.billets/expected_k)*expected_p
    final_events = r.billets*expected_p*(cuts+1)
    front = r.billets*expected_p*q.front_scrap_m
    length = r.billets*expected_p*cuts*q.cut_length_mm/1000 + front + (pulls*p.saws.puller_mm+final_events*p.saws.final_mm)/1000
    assert r.n_pulls == pulls
    assert r.scrap.front_scrap_kg == pytest.approx(front*w, rel=2e-12)
    assert r.scrap.puller_saw_kg == pytest.approx(pulls*p.saws.puller_mm/1000*w, rel=2e-12)
    assert r.scrap.final_saw_kg == pytest.approx(final_events*p.saws.final_mm/1000*w, rel=2e-12)
    assert r.productivity.extruded_total_kg == pytest.approx(length*w, rel=2e-12)
    assert r.extrusion_time_total_min == pytest.approx(length/q.exit_speed_m_min, rel=2e-12)
    if kind == 'split':
        # Construct two synthetic coefficients around a rounding boundary.
        mass = r.billet_length_mm*cb
        for target, ceiling in [(513.9998,514),(514.0002,515)]:
            other = calculate_case(replace(p,billet_kg_per_mm_override=mass/target),case)
            assert other.profiles_per_billet == 2
            assert other.billet_length_mm == pytest.approx(target)
            assert round(other.billet_length_mm) == 514
            assert other.recommended_billet_length_mm == ceiling
    if expected_remaining:
        assert any('partial multi-billet pull' in message.lower() for message in r.warnings)


@pytest.mark.parametrize('exits,factory,cuts,table_fail,billet_fail', [
    (2,press_a,6,True,False), (3,press_a,6,False,True),
    (3,press_b,6,True,True), (4,press_b,6,False,True),
])
def test_next_cut_candidates_rejected_for_physical_constraints(exits, factory, cuts, table_fail, billet_fail):
    p = factory()
    case = StudyCase(Profile(1.1, exits, 'solid'), Production(21,6000,240,front_scrap_m=1.3,cuts=cuts,butt_mm=15))
    cb,cc=raw_coefficients(p)
    pull = cuts*6+1.3+(p.saws.puller_mm+(cuts+1)*p.saws.final_mm)/1000
    length = (1.1*exits*pull+cc*15)/cb
    p = replace(p,table_length_m=pull+(-.01 if table_fail else .01),
        billet_max_length_mm=length+(-.01 if billet_fail else .01))
    r = calculate_case(p, case)
    assert (pull>p.table_length_m) is table_fail
    assert (length>p.billet_max_length_mm) is billet_fail
    assert not r.viable
    if not table_fail:
        one = next(c for c in r.configurations if c.profiles_per_billet == 1)
        assert one.billet_length_mm == pytest.approx(length, rel=2e-12)
        assert 'billet above maximum' in one.reasons
    else:
        assert any('table' in reason for c in r.configurations for reason in c.reasons)


@pytest.mark.parametrize('limit,offset,valid', [('min',-1e-7,True),('min',1e-7,False),('max',-1e-7,False),('max',1e-7,True),('table',-1e-7,False),('table',1e-7,True)])
def test_boundaries_use_internal_value_not_display_rounding(limit, offset, valid):
    p = press_a()
    cb,cc=raw_coefficients(p)
    pull=5*6+1.3+(3+6*4)/1000
    length=(1.1*2*pull+cc*15)/cb
    kwargs={f'billet_{limit}_length_mm':length+offset} if limit!='table' else {'table_length_m':pull+offset}
    r=calculate_case(press_a(**kwargs), case_a())
    assert r.viable is valid
    if valid:
        assert r.recommended_billet_length_mm == math.ceil(length)
        assert r.billet_length_mm != r.recommended_billet_length_mm


def test_json_process_api_cli_and_field_trace_preserve_physical_input(tmp_path, monkeypatch, capsys):
    p, case=press_a(billet_kg_per_mm_override=.087),case_a(20)
    p2=press_from_dict(json.loads(json.dumps(p.to_dict())))
    case2=case_from_dict(json.loads(json.dumps(case.to_dict())))
    r=calculate_case(p2,case2)
    process=calculate_process(p2, PlanningCase(case2.profile,Process(21,6000,front_scrap_m=1.3,cuts=5,butt_mm=20)))
    assert process.butt_mm == r.butt_mm == 20
    assert process.butt_mass_kg == r.billet.butt_mass_kg
    assert process.butt_equivalent_billet_mm == r.billet.butt_equivalent_billet_mm
    assert json.loads(r.to_json())['billet']['mass_coefficient_source'] == 'user_plant_override'
    assert json.loads(process.to_json())['billet_mass_coefficient_source'] == 'user_plant_override'
    assert 'physical' in format_result(r) and 'user_plant_override' in format_result(r)
    pp,cp=tmp_path/'press.json',tmp_path/'case.json'
    save_press_json(p,pp); save_case_json(case,cp)
    from pyextrusion.cli import main
    monkeypatch.setattr(sys,'argv',['pyextrusion','calculate',str(cp),'--press',str(pp),'--field','billet.butt_equivalent_billet_mm'])
    main()
    assert float(capsys.readouterr().out.strip()) == pytest.approx(r.billet.butt_equivalent_billet_mm)


def test_planning_demand_sequence_comparison_consume_corrected_mass_once():
    p, case=press_a(),case_a(20)
    pc=PlanningCase(case.profile,Process(21,6000,front_scrap_m=1.3,cuts=5,butt_mm=20))
    planned=calculate_planning(p,pc,PlanningRequest.bars(240))
    direct=calculate_case(p,case)
    assert planned.calculation == direct
    annual=calculate_annual_demand(p,case,AnnualDemandSpec('bars',240))
    assert annual.calculation.billet.butt_mass_kg == direct.billet.butt_mass_kg
    sequence=calculate_production_sequence(p,[ProductionOrder('one',pc,PlanningRequest.bars(240)),ProductionOrder('two',pc,PlanningRequest.bars(240))])
    assert sequence.total_fixed_scrap_kg == pytest.approx(2*direct.fixed_scrap_kg)
    assert compare_presses([p],case).results[0] == direct
    assert compare_processes([p,press_b()],pc).results[0].butt_mass_kg == direct.billet.butt_mass_kg


@pytest.mark.parametrize('profile_type,physical_mm', [('solid',15),('hollow',20)])
def test_default_butt_values_remain_physical_thickness(profile_type, physical_mm):
    p=press_a()
    case=StudyCase(Profile(1.1,2,profile_type),Production(21,6000,240,front_scrap_m=1.3,cuts=5))
    r=calculate_case(p,case)
    assert r.butt_mm == physical_mm
    assert r.billet.butt_source == 'default_rule'
    assert r.billet.butt_mass_kg == pytest.approx(raw_coefficients(p)[1]*physical_mm,rel=2e-12)


def test_unsupported_three_pull_detection_subtracts_equivalent_butt_from_limits():
    base=press_a(table_length_m=10)
    cb,cc=raw_coefficients(base)
    useful=2*(7+2+(3+2*4)/1000)/cb
    equivalent=35*cc/cb
    length=3*useful+equivalent
    p=press_a(table_length_m=10,billet_min_length_mm=length-1e-7,billet_max_length_mm=length+1e-7)
    case=StudyCase(Profile(2,1,'solid'),Production(24,7000,3,front_scrap_m=2,cuts=1,butt_mm=35))
    r=calculate_case(p,case)
    assert not r.supported
    assert r.required_profiles_per_billet == 3
    assert not r.viable


def test_physical_economics_delta_uses_butt_mass_without_changing_time():
    p=press_a()
    results=[calculate_case(p,case_a(butt)) for butt in (0,20)]
    costs=BasicCostSpec(120,2.7,scrap_sale_value_per_kg=1.1)
    values=[calculate_basic_economics(costs,EconomicProductionBasis(r.timing.total_hours,r.good_kg_manufactured,r.good_kg_manufactured,r.fixed_scrap_kg)) for r in results]
    old,new=results
    assert old.total_time_min == new.total_time_min
    assert old.productivity.extruded_total_kg == new.productivity.extruded_total_kg
    assert old.scrap.start_kg == new.scrap.start_kg
    assert old.scrap.complexity_kg == new.scrap.complexity_kg
    mass=new.billets*raw_coefficients(p)[1]*20
    assert values[1].raw_material_cost-values[0].raw_material_cost == pytest.approx(mass*2.7)
    assert values[1].scrap_recovery_value-values[0].scrap_recovery_value == pytest.approx(mass*1.1)
    assert values[1].recurring_cost-values[0].recurring_cost == pytest.approx(mass*(2.7-1.1))


def test_mechanical_and_limited_thermal_integration_do_not_double_convert_butt():
    p=press_a()
    r=calculate_case(p,case_a(20))
    args=dict(billet_temperature_c=470,billet_diameter_mm=p.billet_diameter_mm,
        container_diameter_mm=p.container_diameter_mm,extrusion_ratio=r.extrusion_ratio,
        ram_speed_mm_s=r.ram_speed_mm_s,friction_factor_m=.88,die_land_length_mm=5)
    new=aa6063_direct_extrusion_operation_estimate(billet_length_mm=r.billet_length_mm,**args)
    old=aa6063_direct_extrusion_operation_estimate(billet_length_mm=r.billet_useful_length_mm+r.butt_mm,**args)
    cb,cc=raw_coefficients(p)
    expected_upset=(r.billet_useful_length_mm*cb)/cc + r.butt_mm
    assert new.billet_contact_length_mm == pytest.approx(expected_upset,rel=2e-12)
    for name in ('mean_strain_rate_s_1','flow_stress_mpa','breakthrough_increment_mpa','exit_speed_m_min'):
        assert getattr(new,name) == getattr(old,name)
    assert new.pressure_breakdown.container_friction_pressure_mpa > old.pressure_breakdown.container_friction_pressure_mpa
    assert new.required_force_mn > old.required_force_mn
    # Synthetic AA6063 integration only; not a validated plant temperature prediction.
    nt,ot=new.surface_exit_temperature_estimate,old.surface_exit_temperature_estimate
    assert nt.container_wall_temperature_rise_c > ot.container_wall_temperature_rise_c
    assert nt.deformation_temperature_rise_c == ot.deformation_temperature_rise_c
    assert nt.die_land_temperature_rise_c == ot.die_land_temperature_rise_c
    from pyextrusion.engineering import ram_power_kw_from_force_mn_speed_mm_s, check_force_capacity
    assert ram_power_kw_from_force_mn_speed_mm_s(new.required_force_mn,r.ram_speed_mm_s) == pytest.approx(new.required_force_mn*r.ram_speed_mm_s)
    assert check_force_capacity(new.required_force_mn,30).margin_mn == pytest.approx(30-new.required_force_mn)
