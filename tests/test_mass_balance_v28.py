import pytest

from pyextrusion import PressSpec, ProfileSpec, SawSpec, calculate_simple


def _press(*, saws=SawSpec(4, 4, 4)):
    return PressSpec(
        name="Mass balance press",
        nominal_force_t=2500,
        container_diameter_mm=210,
        billet_diameter_mm=203,
        billet_min_mm=400,
        billet_max_mm=1200,
        table_length_m=54,
        dead_time_sec=15,
        saws=saws,
    )


def _physical_extruded_mass(result):
    return (
        result.good_kg_manufactured
        + result.scrap.front_scrap_kg
        + result.scrap.puller_saw_kg
        + result.scrap.final_saw_kg
    )


def test_one_pull_kerfs_are_reserved_in_billet_and_extrusion_time():
    r = calculate_simple(
        _press(),
        linear_weight_kg_m=0.819,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=140,
        front_scrap_m=2,
        butt_mm=15,
        cuts=7,
    )

    assert r.recommended_configuration == "1_billet_1_profile"
    assert r.billets_per_pull == 1

    physical_mass = _physical_extruded_mass(r)
    billet_useful_mass = r.billet_useful_length_mm * r.billet.kg_per_mm * r.billets
    assert billet_useful_mass == pytest.approx(physical_mass)

    physical_length_m = physical_mass / (0.819 * 2)
    assert r.timing.extrusion_total_min == pytest.approx(
        physical_length_m / r.exit_speed_m_min
    )


def test_raw_material_closes_for_one_pull_including_butt_and_billet_saw():
    r = calculate_simple(
        _press(),
        linear_weight_kg_m=0.819,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=140,
        front_scrap_m=2,
        butt_mm=15,
        cuts=7,
    )

    loaded_billet_mass = r.billet_length_mm * r.billet.kg_per_mm * r.billets
    physical_from_billet = _physical_extruded_mass(r) + r.scrap.butt_kg
    assert loaded_billet_mass == pytest.approx(physical_from_billet)

    purchased_with_billet_saw = loaded_billet_mass + r.scrap.billet_saw_kg
    accounted_raw_material = physical_from_billet + r.scrap.billet_saw_kg
    assert purchased_with_billet_saw == pytest.approx(accounted_raw_material)


def test_zero_downstream_kerfs_add_no_physical_length():
    r = calculate_simple(
        _press(saws=SawSpec(0, 0, 0)),
        linear_weight_kg_m=0.819,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=140,
        front_scrap_m=2,
        butt_mm=15,
        cuts=7,
    )

    expected_segment_m = 7 * 7 + 2
    expected_useful_mm = (0.819 * 2 * expected_segment_m) / r.billet.kg_per_mm
    assert r.billet_useful_length_mm == pytest.approx(expected_useful_mm)
    assert r.scrap.puller_saw_kg == 0
    assert r.scrap.final_saw_kg == 0


def test_double_profile_reserves_each_pull_kerfs_and_closes_mass():
    r = calculate_simple(
        _press(),
        linear_weight_kg_m=0.4,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=20,
        cut_length_mm=7000,
        bars_requested=100,
        front_scrap_m=2,
        butt_mm=20,
    )

    assert r.recommended_configuration == "1_billet_2_profiles"
    assert r.profiles_per_billet == 2

    physical_mass = _physical_extruded_mass(r)
    billet_useful_mass = r.billet_useful_length_mm * r.billet.kg_per_mm * r.billets
    assert billet_useful_mass == pytest.approx(physical_mass)

    physical_length_m = physical_mass / 0.4
    assert r.timing.extrusion_total_min == pytest.approx(
        physical_length_m / r.exit_speed_m_min
    )


def test_full_multi_billet_pull_distributes_shared_kerfs_and_closes_mass():
    r = calculate_simple(
        _press(),
        linear_weight_kg_m=5.0,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=15,
        cut_length_mm=7000,
        bars_requested=12,
        front_scrap_m=2,
        butt_mm=15,
        cuts=2,
    )

    assert r.recommended_configuration == "k_billets_1_profile"
    assert r.billets_per_pull >= 2
    assert r.remaining_billets == 0

    physical_mass = _physical_extruded_mass(r)
    billet_useful_mass = r.billet_useful_length_mm * r.billet.kg_per_mm * r.billets
    assert billet_useful_mass == pytest.approx(physical_mass)


def test_partial_multi_billet_pull_uses_exact_order_time_and_warns_about_shared_kerf():
    r = calculate_simple(
        _press(),
        linear_weight_kg_m=5.0,
        exits=1,
        profile_type="solid",
        exit_speed_m_min=15,
        cut_length_mm=7000,
        bars_requested=10,
        front_scrap_m=2,
        butt_mm=15,
        cuts=2,
    )

    assert r.recommended_configuration == "k_billets_1_profile"
    assert r.remaining_billets > 0

    physical_mass = _physical_extruded_mass(r)
    physical_length_m = physical_mass / 5.0
    assert r.timing.extrusion_total_min == pytest.approx(
        physical_length_m / r.exit_speed_m_min
    )
    assert any("partial multi-billet pull" in warning.lower() for warning in r.warnings)


def test_startup_and_complexity_remain_modeled_allowances_not_physical_extruded_mass():
    r = calculate_simple(
        _press(),
        linear_weight_kg_m=0.819,
        exits=2,
        profile_type="solid",
        exit_speed_m_min=24,
        cut_length_mm=7000,
        bars_requested=140,
        front_scrap_m=2,
        butt_mm=15,
        cuts=7,
        complexity="normal",
    )

    expected_physical_extruded_losses = (
        r.scrap.front_scrap_kg
        + r.scrap.puller_saw_kg
        + r.scrap.final_saw_kg
    )
    assert r.scrap.extruded_losses_kg == pytest.approx(expected_physical_extruded_losses)
    assert r.productivity.extruded_total_kg == pytest.approx(
        r.good_kg_manufactured + expected_physical_extruded_losses
    )
    assert r.scrap.start_kg > 0
    assert r.scrap.complexity_kg > 0
    assert r.scrap.total_kg > r.scrap.fixed_kg
