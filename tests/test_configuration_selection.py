"""Explicit production-family choices preserve topology and full physical balances."""
from dataclasses import replace
from datetime import datetime,timezone
import json
import math
import pytest

from pyextrusion import (
    PressSpec,SawSpec,ProfileSpec,ProcessSpec,ProductionSpec,PlanningCase,StudyCase,StudyInput,
    PlanningRequest,ProductionOrder,calculate_process,calculate_planning,calculate_case,calculate,
    calculate_simple,calculate_production_sequence,compare_processes,compare_planning,
    planning_case_to_dict,planning_case_from_dict,case_to_dict,case_from_dict,study_to_dict,study_from_dict,
    production_sequence_to_dict,production_sequence_from_dict,save_planning_case_json,load_planning_case_json,
    InvalidProductionInputError,UnsupportedSchemaVersionError,validate_study,validate_planning_case,
)

SINGLE='1_billet_1_profile'
DOUBLE='1_billet_2_profiles'
MULTI='k_billets_1_profile'


def press(**changes):
    return PressSpec(**{'name':'Explicit-selection test press','nominal_size_in':9,
        'billet_diameter_mm':228,'container_diameter_mm':236,'billet_min_length_mm':400,
        'billet_max_length_mm':1300,'table_length_m':60,'dead_time_sec':15,
        'billet_kg_per_mm_override':0.110,'saws':SawSpec(0,0,0),**changes})


def case(**changes):
    return PlanningCase(ProfileSpec(1.8,1,'solid',1.8/2700),
        ProcessSpec(**{'exit_speed_m_min':25,'cut_length_mm':6000,'trim_total_per_billet_m':3,
            'butt_mm':20,**changes}))


def test_fewer_cuts_shorten_the_billet_without_changing_family():
    lengths=[]
    for cuts in (8,7,6):
        result=calculate_planning(press(),case(configuration=SINGLE,cuts=cuts),PlanningRequest.bars(160))
        p=result.process;c=result.calculation
        assert p.selected_configuration==SINGLE and result.selected_configuration==SINGLE
        assert p.configuration_source=='user_override'
        assert p.profiles_per_billet==1 and p.billets_per_pull==1
        assert p.bars_per_billet==cuts and c.bars_per_billet==cuts
        butt_mass=2700*math.pi*(236/1000)**2/4*(20/1000)
        expected=((cuts*6+3)*1.8+butt_mass)/0.110
        assert p.billet_length_mm==pytest.approx(expected)
        assert c.billet_length_mm==p.billet_length_mm
        assert c.billets==math.ceil(160/cuts)
        assert c.bars_manufactured==c.billets*cuts
        assert c.selected_configuration==c.status.selected_configuration==c.process.selected_configuration==SINGLE
        lengths.append(p.billet_length_mm)
    assert lengths[0]>lengths[1]>lengths[2]


def test_recommendation_remains_distinct_from_selected_geometry_and_trace():
    result=calculate_planning(press(),case(configuration=SINGLE,cuts=6),PlanningRequest.bars(160))
    p=result.process;c=result.calculation
    assert p.recommended_configuration==DOUBLE
    assert p.automatic_recommendation.name==DOUBLE
    assert p.automatic_recommendation.billet_length_mm>p.billet_length_mm
    assert p.requested_configuration_result.name==SINGLE
    assert c.recommended_configuration==c.status.recommended_configuration==DOUBLE
    assert c.automatic_recommendation==p.automatic_recommendation
    assert c.requested_configuration==c.process.requested_configuration==SINGLE
    data=json.loads(result.to_json())
    assert data['selected_configuration']==SINGLE
    assert data['process']['automatic_recommendation']['name']==DOUBLE
    assert data['calculation']['selected_configuration']==SINGLE


@pytest.mark.parametrize('selection,extra',[(SINGLE,{}),(DOUBLE,{}),(MULTI,{'billets_per_pull':3})])
def test_unforced_and_forced_process_geometry_match_order_geometry(selection,extra):
    configured=case(configuration=selection,cuts=2 if selection==MULTI else 6,**extra)
    if selection==MULTI:configured=replace(configured,profile=ProfileSpec(1.8,2,'solid'))
    p=calculate_process(press(),configured)
    c=calculate_planning(press(),configured,PlanningRequest.bars(157)).calculation
    assert p.viable and c.viable
    for field in ('cuts','billets_per_pull','profiles_per_billet','bars_per_billet','billet_length_mm','table_occupancy_length_m'):
        assert getattr(c,field)==getattr(p,field)


def test_double_pull_uses_total_trim_once_and_two_dead_time_events_per_billet():
    result=calculate_planning(press(),case(configuration=DOUBLE,cuts=5),PlanningRequest.billets(4))
    c=result.calculation;p=result.process
    assert result.selected_configuration==DOUBLE
    assert p.profiles_per_billet==2 and p.trim_per_pull_m==1.5
    assert c.bars_manufactured==4*2*5
    assert c.scrap.front_scrap_kg==pytest.approx(4*3*1.8)
    assert c.n_pulls==8 and c.dead_time_events==7
    assert c.extrusion_time_total_min==pytest.approx(4*(2*5*6+3)/25)
    assert c.total_time_min==pytest.approx(c.extrusion_time_total_min+7*15/60)


@pytest.mark.parametrize('trim',[0,2])
def test_exact_multi_billet_count_and_partial_last_pull_have_independent_balances(trim):
    equipment=press(billet_min_length_mm=100,saws=SawSpec(6,5,5))
    configured=PlanningCase(ProfileSpec(1.8,2,'solid'),ProcessSpec(exit_speed_m_min=25,cut_length_mm=6000,
        trim_total_per_billet_m=trim,butt_mm=20,cuts=2,configuration=MULTI,billets_per_pull=3))
    result=calculate_planning(equipment,configured,PlanningRequest.billets(5));c=result.calculation
    assert result.process.billets_per_pull==c.billets_per_pull==3
    assert c.n_pulls==2 and c.full_pulls==1 and c.remaining_billets==2
    assert c.production.internal_billet_transitions==3
    assert c.bars_manufactured==5*2*2
    events=5*(2+1) if trim else 5*2+2
    combined_weight=2*1.8
    good=5*2*2*6*1.8
    front=5*trim*combined_weight
    puller=2*0.005*combined_weight
    final=events*0.005*combined_weight
    butt=5*2700*math.pi*(236/1000)**2/4*0.020
    billet_saw=5*6*0.110
    assert c.production.final_saw_events==events
    assert c.production.puller_saw_events==2
    assert c.good_kg_manufactured==pytest.approx(good)
    assert c.scrap.front_scrap_kg==pytest.approx(front)
    assert c.scrap.butt_kg==pytest.approx(butt)
    assert c.scrap.billet_saw_kg==pytest.approx(billet_saw)
    assert c.scrap.puller_saw_kg==pytest.approx(puller)
    assert c.scrap.final_saw_kg==pytest.approx(final)
    assert c.productivity.extruded_total_kg==pytest.approx(good+front+puller+final)
    length=5*(2*6+trim)+2*0.005+events*0.005
    assert c.extrusion_time_total_min==pytest.approx(length/25)
    assert c.dead_time_events==4
    assert c.total_time_min==pytest.approx(length/25+4*15/60)


@pytest.mark.parametrize('planning_request',[PlanningRequest.bars(157),PlanningRequest.kg(1500),PlanningRequest.metres(1000),
    PlanningRequest.billets(5),PlanningRequest.minutes(20),PlanningRequest.hours(0.5)])
def test_every_planning_mode_retains_the_explicit_family(planning_request):
    result=calculate_planning(press(),case(configuration=SINGLE,cuts=6),planning_request)
    assert result.process.selected_configuration==SINGLE and result.calculation.selected_configuration==SINGLE
    assert result.bars_per_billet==6
    if planning_request.mode in {'minutes','hours'}:assert result.time_used_min<=result.available_time_min+1e-12


@pytest.mark.parametrize('selection,changes',[(SINGLE,{'cuts':3}),(DOUBLE,{'cuts':8}),(MULTI,{'cuts':4,'billets_per_pull':3})])
def test_impossible_choice_is_nonviable_without_falling_back_to_recommendation(selection,changes):
    result=calculate_planning(press(),case(configuration=selection,**changes),PlanningRequest.bars(160))
    assert result.process.supported and not result.process.viable
    assert result.selected_configuration is None and result.calculation is None
    assert result.planned_bars==result.planned_billets==0
    assert result.process.requested_configuration_result.name==selection
    assert not result.process.requested_configuration_result.valid
    assert result.process.requested_configuration_result.reasons
    assert any('no alternative' in w for w in result.process.warnings)


def test_single_pull_does_not_add_billets_to_fill_an_underused_table():
    p=calculate_process(press(billet_min_length_mm=100),case(configuration=SINGLE,cuts=2))
    assert p.billets_per_pull==1
    assert p.table_occupancy_length_m==15
    assert p.bars_per_billet==2
    assert p.automatic_recommendation.billets_per_pull>1 or p.automatic_recommendation.profiles_per_billet==2


@pytest.mark.parametrize('fields',[
    {'configuration':'automatic'}, {'configuration':False}, {'configuration':[]},
    {'billets_per_pull':2}, {'configuration':SINGLE,'billets_per_pull':1},
    {'configuration':DOUBLE,'billets_per_pull':2}, {'configuration':MULTI},
    *[{'configuration':MULTI,'billets_per_pull':v} for v in [True,False,1,0,-1,2.0,'2',float('nan'),float('inf')]],
])
def test_selection_validation_is_strict_across_both_public_specs_and_raw_input(fields):
    with pytest.raises(InvalidProductionInputError):case(**fields)
    with pytest.raises(InvalidProductionInputError):ProductionSpec(exit_speed_m_min=25,cut_length_mm=6000,bars_requested=160,**fields)
    raw=StudyInput(press=press(),profile=ProfileSpec(1.8,1,'solid'),exit_speed_m_min=25,cut_length_mm=6000,bars_requested=160,
        trim_total_per_billet_m=3,**fields)
    with pytest.raises(InvalidProductionInputError):calculate(raw)
    assert any(m.level=='error' for m in validate_study(raw))


def test_absurd_billet_count_is_a_controlled_numeric_error():
    with pytest.raises(InvalidProductionInputError,match='finite numeric range'):
        calculate_process(press(),case(configuration=MULTI,billets_per_pull=10**1000))


def test_selected_case_round_trips_through_every_conversion_and_json(tmp_path):
    original=case(configuration=MULTI,billets_per_pull=3,cuts=2)
    for candidate in [planning_case_from_dict(planning_case_to_dict(original)),original.to_study_case(157).to_planning_case(),
        original.to_study_case(157).to_study_input(press()).to_case().to_planning_case()]:
        assert candidate==original
    path=save_planning_case_json(original,tmp_path/'case.json')
    assert json.loads(path.read_text())['schema_version']=='1.2'
    assert load_planning_case_json(path)==original
    production=original.to_study_case(157)
    assert case_from_dict(case_to_dict(production))==production
    raw=production.to_study_input(press())
    assert study_from_dict(study_to_dict(raw))==raw
    assert not validate_planning_case(original)
    automatic=original.with_process(configuration=None,billets_per_pull=None)
    assert automatic.to_dict()['schema_version']=='1.1'
    assert 'configuration' not in automatic.to_dict()['process']


def test_old_schema_cannot_silently_store_or_load_a_selection():
    configured=case(configuration=SINGLE,cuts=6)
    with pytest.raises(UnsupportedSchemaVersionError):planning_case_to_dict(configured,schema_version='1.1')
    data=configured.to_dict();data['schema_version']='1.1'
    with pytest.raises(UnsupportedSchemaVersionError):planning_case_from_dict(data)


def test_simple_api_and_comparisons_use_selected_results():
    kwargs=dict(linear_weight_kg_m=1.8,exits=1,profile_type='solid',exit_speed_m_min=25,cut_length_mm=6000,
        bars_requested=157,trim_total_per_billet_m=3,butt_mm=20,cuts=6,configuration=SINGLE,section_per_exit_m2=1.8/2700)
    result=calculate_simple(press(),**kwargs)
    direct=calculate_case(press(),case(configuration=SINGLE,cuts=6).to_study_case(157))
    assert result==direct
    assert all(r.selected_configuration==SINGLE for r in compare_processes([press(),press(name='Other')],case(configuration=SINGLE,cuts=6)).results)
    assert all(r.selected_configuration==SINGLE for r in compare_planning([press(),press(name='Other')],case(configuration=SINGLE,cuts=6),PlanningRequest.bars(157)).results)


def test_sequence_keeps_each_orders_family_and_round_trips_selection_schema():
    orders=[ProductionOrder(order_id='single',case=case(configuration=SINGLE,cuts=6),request=PlanningRequest.bars(157)),
            ProductionOrder(order_id='double',case=case(configuration=DOUBLE,cuts=5),request=PlanningRequest.billets(4))]
    start=datetime(2026,11,2,8,tzinfo=timezone.utc)
    data=production_sequence_to_dict(press(),orders,start_at=start)
    assert data['schema_version']=='1.2'
    equipment,restored,timestamp=production_sequence_from_dict(data)
    assert restored==tuple(orders) and timestamp==start
    result=calculate_production_sequence(equipment,restored,start_at=timestamp)
    assert [e.planning.selected_configuration for e in result.orders]==[SINGLE,DOUBLE]
    assert [e.planning.bars_per_billet for e in result.orders]==[6,10]
    with pytest.raises(UnsupportedSchemaVersionError):production_sequence_to_dict(equipment,orders,schema_version='1.1')


@pytest.mark.parametrize('trim',[0,2])
def test_time_window_uses_actual_partial_pull_kerfs_at_the_boundary(trim):
    equipment=press(billet_min_length_mm=100,saws=SawSpec(6,5,5))
    configured=PlanningCase(ProfileSpec(1.8,2,'solid'),ProcessSpec(exit_speed_m_min=25,cut_length_mm=6000,
        trim_total_per_billet_m=trim,butt_mm=20,cuts=2,configuration=MULTI,billets_per_pull=3))
    two=calculate_planning(equipment,configured,PlanningRequest.billets(2))
    exact=two.calculation.total_time_min
    below=calculate_planning(equipment,configured,PlanningRequest.minutes(exact-1e-7))
    boundary=calculate_planning(equipment,configured,PlanningRequest.minutes(exact))
    assert below.planned_billets==1 and boundary.planned_billets==2
    assert below.time_used_min==below.calculation.total_time_min
    assert boundary.time_used_min==boundary.calculation.total_time_min
    assert boundary.time_remaining_min==pytest.approx(0)
    assert below.additional_time_for_next_billet_min==pytest.approx(1e-7)


def test_cli_json_text_and_field_glossary_expose_adopted_configuration(tmp_path,capsys,monkeypatch):
    import sys
    from pyextrusion import save_press_json,describe_field,format_planning_result,format_result
    from pyextrusion.cli import main
    configured=case(configuration=SINGLE,cuts=6)
    case_path=save_planning_case_json(configured,tmp_path/'case.json')
    press_path=save_press_json(press(),tmp_path/'press.json')
    monkeypatch.setattr(sys,'argv',['pyextrusion','plan',str(case_path),'--press',str(press_path),'--bars','157','--format','json'])
    main()
    result=json.loads(capsys.readouterr().out)
    assert result['selected_configuration']==SINGLE and result['recommended_configuration']==DOUBLE
    assert describe_field('status.selected_configuration').path=='status.selected_configuration'
    planned=calculate_planning(press(),configured,PlanningRequest.bars(157))
    for text in (format_planning_result(planned),format_result(planned.calculation)):
        assert f'Selected config:         {SINGLE}' in text
        assert f'Automatic recommendation: {DOUBLE}' in text


def test_legacy_trim_override_only_applies_to_explicit_multibillet_family():
    equipment=press(billet_min_length_mm=100)
    profile=ProfileSpec(1.8,2,'solid')
    common=dict(exit_speed_m_min=25,cut_length_mm=6000,front_scrap_m=2,multi_billet_front_scrap_m=1.5,cuts=2)
    single=calculate_process(equipment,PlanningCase(profile,ProcessSpec(**common,configuration=SINGLE)))
    multi=calculate_process(equipment,PlanningCase(profile,ProcessSpec(**common,configuration=MULTI,billets_per_pull=3)))
    assert single.applied_front_scrap_m==2
    assert multi.applied_front_scrap_m==1.5
    assert single.billets_per_pull==1 and multi.billets_per_pull==3


@pytest.mark.parametrize('selection,k', [(SINGLE, None), (DOUBLE, None), (MULTI, 3)])
def test_automatic_cuts_optimize_only_within_requested_family(selection, k):
    equipment = press(billet_min_length_mm=100)
    configured = case(configuration=selection, billets_per_pull=k)
    resolved = calculate_process(equipment, configured)
    feasible = []
    for cuts in range(1, math.floor(equipment.table_length_m / 6) + 1):
        candidate = calculate_process(equipment, configured.with_process(cuts=cuts))
        if candidate.viable:
            feasible.append(candidate)
    assert feasible and resolved.viable
    assert resolved.selected_configuration == selection
    assert resolved.billets_per_pull == (k or 1)
    assert resolved.billet_length_mm == max(p.billet_length_mm for p in feasible)
    assert resolved.automatic_recommendation == calculate_process(
        equipment, configured.with_process(configuration=None, billets_per_pull=None)
    ).automatic_recommendation


def test_exact_candidate_is_not_identified_by_family_name_alone():
    equipment = press(billet_min_length_mm=100)
    result = calculate_process(equipment, case(configuration=MULTI, billets_per_pull=2, cuts=2))
    same_family = [c for c in result.configurations if c.name == MULTI]
    assert len(same_family) == 2
    assert {c.billets_per_pull for c in same_family} == {2, 4}
    assert result.automatic_recommendation == calculate_process(
        equipment, case(cuts=2)
    ).automatic_recommendation
    assert result.requested_configuration_result.billets_per_pull == result.billets_per_pull == 2
    assert result.requested_configuration_result in same_family


@pytest.mark.parametrize('trim', [0, 2])
@pytest.mark.parametrize('billets', [1, 2, 3, 4, 5, 6, 7])
def test_time_window_fits_maximum_actual_order_at_every_group_boundary(trim, billets):
    equipment = press(billet_min_length_mm=100, saws=SawSpec(6, 5, 5))
    configured = case(configuration=MULTI, billets_per_pull=3, cuts=2,
                      trim_total_per_billet_m=trim)
    actual = calculate_planning(equipment, configured, PlanningRequest.billets(billets))
    next_order = calculate_planning(equipment, configured, PlanningRequest.billets(billets + 1))
    # Use independently requested orders to bracket full and partial pulls.
    available = (actual.time_used_min + next_order.time_used_min) / 2
    window = calculate_planning(equipment, configured, PlanningRequest.minutes(available))
    assert window.planned_billets == billets
    assert window.time_used_min == actual.time_used_min == window.calculation.total_time_min
    assert window.time_used_min <= available < next_order.time_used_min
    assert window.additional_time_for_next_billet_min == pytest.approx(next_order.time_used_min - available)


def test_sequence_schema_guards_envelope_and_nested_selection_without_mutating_input():
    from copy import deepcopy

    orders = [
        ProductionOrder('automatic', case(cuts=6), PlanningRequest.billets(2)),
        ProductionOrder('selected', case(configuration=SINGLE, cuts=6), PlanningRequest.billets(2)),
    ]
    original = production_sequence_to_dict(press(), orders)
    snapshot = deepcopy(original)
    assert original['schema_version'] == '1.2'
    assert 'configuration' not in original['orders'][0]['case']['process']
    assert production_sequence_from_dict(original)[1] == tuple(orders)
    assert original == snapshot
    # Outer 1.2 can supply the schema when the nested case omits its envelope.
    inherited = deepcopy(original)
    inherited['orders'][1]['case'].pop('schema_version')
    assert production_sequence_from_dict(inherited)[1] == tuple(orders)
    for old_outer, old_inner in [(True, False), (False, True), (True, True)]:
        downgraded = deepcopy(original)
        if old_outer:
            downgraded['schema_version'] = '1.1'
        if old_inner:
            downgraded['orders'][1]['case']['schema_version'] = '1.1'
        with pytest.raises(UnsupportedSchemaVersionError):
            production_sequence_from_dict(downgraded)


def test_nonviable_order_exposes_requested_candidate_but_no_production():
    from pyextrusion import format_result, format_process_comparison

    equipment = press()
    configured = case(configuration=SINGLE, cuts=3)
    process = calculate_process(equipment, configured)
    result = calculate_case(equipment, configured.to_study_case(157))
    assert not result.viable and result.supported
    assert result.selected_configuration is None
    assert result.automatic_recommendation.valid
    assert result.requested_configuration_result == process.requested_configuration_result
    assert result.billets == result.bars_manufactured == result.n_pulls == 0
    assert result.production.final_saw_events == 0
    assert 'Selected config:         none' in format_result(result)
    comparison = compare_processes([equipment, press(name='Second')], configured)
    assert DOUBLE not in format_process_comparison(comparison)
