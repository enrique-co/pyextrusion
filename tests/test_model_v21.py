import json
import math
import subprocess
import sys
import os
from pathlib import Path

import pytest

from pyextrusion import (
    PlanningCase,
    PlanningRequest,
    Press,
    Process,
    Profile,
    calculate_case,
    calculate_planning,
    calculate_simple,
    load_planning_case_json,
    save_planning_case_json,
)


def press8(*, table=54, billet_min=450, billet_max=1200, saws=None):
    kwargs = {}
    if saws is not None:
        kwargs["saws"] = saws
    return Press(
        name="V2.1 8-inch",
        nominal_size_in=8,
        table_length_m=table,
        billet_min_length_mm=billet_min,
        billet_max_length_mm=billet_max,
        **kwargs,
    )


def test_v21_dynamic_multi_billet_can_exceed_three_billets_per_pull():
    # One 8 m bar + 2 m front scrap creates a valid nominal 10 m segment.
    # Physical table occupancy also reserves puller/final saw kerfs. Five
    # complete billet contributions still fit the 54 m table.
    p = press8()
    r = calculate_simple(
        p,
        linear_weight_kg_m=8.0,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=18,
        cut_length_mm=8000,
        bars_requested=100,
        front_scrap_m=2,
    )
    assert r.viable and r.supported
    assert r.recommended_configuration == "k_billets_1_profile"
    assert r.cuts == 1
    assert r.billets_per_pull == 5
    assert r.cuts_per_pull == 5
    assert r.bars_per_pull == 5
    expected_occupancy = (
        5 * (8.0 + 2.0)
        + (p.saws.puller_mm / 1000.0)
        + (5 + 1) * (p.saws.final_mm / 1000.0)
    )
    assert r.table_occupancy_length_m == pytest.approx(expected_occupancy)


def test_v21_billet_first_does_not_shorten_billet_to_fit_more_billets():
    # With this profile, one-profile optimization selects 2 cuts and a billet
    # near the press maximum. Reducing to 1 cut would allow more billets on
    # the table, but billet-first explicitly forbids that optimization direction.
    r = calculate_simple(
        press8(),
        linear_weight_kg_m=4.8,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=15,
        cut_length_mm=9800,
        bars_requested=100,
        front_scrap_m=2,
    )
    one = next(c for c in r.configurations if c.name == "k_billets_1_profile")
    assert one.valid
    assert one.cuts == 2
    assert one.billet_length_mm > 1190
    assert one.billet_length_mm <= 1200
    assert one.billets_per_pull == 2

    # A deliberately shorter 1-cut candidate would fit four nominal segments
    # on the same table, but must not replace the 2-cut billet-first candidate.
    cut_m = 9.8
    short_segment = cut_m + 2.0
    assert math.floor(54 / short_segment) == 4
    short_billet = (4.8 * short_segment) / r.billet.kg_per_mm + r.butt_mm
    assert short_billet < one.billet_length_mm


def test_v21_multi_billet_front_scrap_reoptimizes_billet_before_k():
    p = Press(
        name="Measured mass press",
        nominal_size_in=8,
        table_length_m=54,
        billet_kg_per_mm_override=0.087,
    )
    base = calculate_simple(
        p,
        linear_weight_kg_m=4.0,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=15,
        cut_length_mm=7000,
        bars_requested=100,
        front_scrap_m=2,
        multi_billet_front_scrap_m=1,
    )
    cfg = next(c for c in base.configurations if c.name == "k_billets_1_profile")
    assert cfg.valid and cfg.billets_per_pull >= 2
    assert cfg.front_scrap_per_billet_m == pytest.approx(1.0)
    nominal_segment = cfg.cuts * 7.0 + 1.0
    final_kerf_m = p.saws.final_mm / 1000.0
    shared_kerf_m = (p.saws.puller_mm + p.saws.final_mm) / 1000.0
    expected_physical_per_billet = (
        nominal_segment
        + cfg.cuts * final_kerf_m
        + shared_kerf_m / cfg.billets_per_pull
    )
    expected_useful = 4.0 * expected_physical_per_billet / 0.087
    assert cfg.length_per_billet_m == pytest.approx(expected_physical_per_billet)
    assert cfg.billet_useful_length_mm == pytest.approx(expected_useful)
    assert cfg.billet_length_mm == pytest.approx(expected_useful + base.butt_mm)
    assert base.process.applied_front_scrap_source == "multi_billet_user_override"


def test_v21_multi_billet_cuts_ratio_uses_complete_pull():
    r = calculate_simple(
        press8(),
        linear_weight_kg_m=8.0,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=18,
        cut_length_mm=8000,
        bars_requested=100,
        front_scrap_m=2,
    )
    assert r.theoretical_cuts == 6
    assert r.cuts == 1
    assert r.billets_per_pull == 5
    assert r.cuts_per_pull == 5
    assert r.cuts_ratio == pytest.approx(5 / 6)
    # This is intentionally not the old per-billet ratio of 1/6.
    assert r.cuts_ratio != pytest.approx(1 / 6)


def test_v21_multi_billet_puller_and_final_saw_are_per_pull_with_partial_last_pull():
    p = press8()
    # This process yields k=5 and 1 bar/billet. Seven requested bars therefore
    # create one full 5-billet pull and one partial 2-billet pull.
    r = calculate_simple(
        p,
        linear_weight_kg_m=8.0,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=18,
        cut_length_mm=8000,
        bars_requested=7,
        front_scrap_m=2,
    )
    assert r.billets_per_pull == 5
    assert r.billets == 7
    assert r.full_pulls == 1
    assert r.remaining_billets == 2
    assert r.n_pulls == 2

    kg_m_total = 8.0
    expected_puller = (p.saws.puller_mm / 1000) * kg_m_total * 2
    assert r.scrap.puller_saw_kg == pytest.approx(expected_puller)

    expected_final_events = 1 * (1 * 5 + 1) + (1 * 2 + 1)
    expected_final = (p.saws.final_mm / 1000) * kg_m_total * expected_final_events
    assert r.scrap.final_saw_kg == pytest.approx(expected_final)
    assert any("partial multi-billet pull" in w.lower() for w in r.warnings)


def test_v21_three_or_more_profiles_per_billet_is_controlled_unsupported_scenario():
    # Very light profile: one or two sequential profiles leave the billet below
    # the 450 mm press minimum, while three would make the billet valid.
    r = calculate_simple(
        press8(),
        linear_weight_kg_m=0.25,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=20,
        cut_length_mm=9800,
        bars_requested=100,
        front_scrap_m=2,
    )
    assert not r.viable
    assert not r.supported
    assert r.required_profiles_per_billet == 3
    assert r.status.required_profiles_per_billet == 3
    assert r.recommended_configuration is None
    assert "More than 2 profiles per billet is not supported" in r.unsupported_reason
    assert any("More than 2 profiles per billet is not supported" in w for w in r.warnings)
    assert all(c.name != "1_billet_3_profiles" for c in r.configurations)


def test_v21_process_spec_and_planning_case_have_no_order_quantity():
    pc = PlanningCase(
        profile=Profile(1.35, 2, "solid"),
        process=Process(
            exit_speed_m_min=24,
            cut_length_mm=7000,
            front_scrap_m=2,
            complexity="normal",
        ),
    )
    payload = pc.to_dict()
    assert "bars_requested" not in payload["process"]
    assert "supplement_10_pct" not in payload["process"]
    result = calculate_planning(press8(), pc, PlanningRequest.bars(300))
    assert result.process_viable
    assert result.process_supported
    assert result.normalized_target_bars == 300
    assert result.planned_billets > 0


def test_v22_planning_case_json_schema_11_round_trip(tmp_path):
    pc = PlanningCase(
        Profile(1.2, 2, "hollow"),
        Process(18, 6500, front_scrap_m=1.5, complexity="medium"),
    )
    path = tmp_path / "planning_case.json"
    save_planning_case_json(pc, path)
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == "1.1"
    assert set(raw) == {"schema_version", "profile", "process"}
    assert load_planning_case_json(path) == pc


def test_v21_planning_exact_billets_respects_partial_pull_grouping():
    pc = PlanningCase(
        Profile(8.0, 1, "solid"),
        Process(18, 8000, front_scrap_m=2),
    )
    plan = calculate_planning(press8(), pc, PlanningRequest.billets(7))
    assert plan.request_fulfilled
    assert plan.planned_billets == 7
    assert plan.calculation is not None
    assert plan.calculation.billets_per_pull == 5
    assert plan.calculation.full_pulls == 1
    assert plan.calculation.remaining_billets == 2
    assert plan.calculation.n_pulls == 2


def test_v21_planning_cli_accepts_quantity_free_planning_case(tmp_path):
    from pyextrusion import save_press_json

    ppath = tmp_path / "press.json"
    cpath = tmp_path / "planning.json"
    save_press_json(press8(), ppath)
    save_planning_case_json(
        PlanningCase(Profile(1.35, 2, "solid"), Process(24, 7000, front_scrap_m=2)),
        cpath,
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyextrusion.cli",
            "plan",
            str(cpath),
            "--press",
            str(ppath),
            "--bars",
            "300",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    payload = json.loads(proc.stdout)
    assert payload["planned_billets"] > 0
    assert payload["normalized_target_bars"] == 300
    assert payload["reference"]["status"]["supported"] is True
