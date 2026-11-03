"""Synthetic example: fewer cuts keep the requested single-pull family."""
from pyextrusion import (
    PressSpec,SawSpec,ProfileSpec,ProcessSpec,PlanningCase,PlanningRequest,calculate_planning,
)

press=PressSpec(name='Synthetic press',nominal_size_in=9,billet_diameter_mm=228,container_diameter_mm=236,
    billet_min_length_mm=400,billet_max_length_mm=1300,table_length_m=60,dead_time_sec=15,
    billet_kg_per_mm_override=0.110,saws=SawSpec(0,0,0))
case=PlanningCase(ProfileSpec(1.8,1,'solid'),ProcessSpec(exit_speed_m_min=25,cut_length_mm=6000,
    trim_total_per_billet_m=3,butt_mm=20,configuration='1_billet_1_profile'))
for cuts in (8,7,6):
    plan=calculate_planning(press,case.with_process(cuts=cuts),PlanningRequest.bars(160))
    assert plan.selected_configuration=='1_billet_1_profile'
    print(f'{cuts} cuts: {plan.billet_length_mm:.3f} mm, {plan.planned_billets} billets; automatic reference: {plan.recommended_configuration}')
