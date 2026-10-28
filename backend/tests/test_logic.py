"""Deterministic tests: no randomness, so the results never change."""

import random
from datetime import datetime

import pytest

from simulator import (
    ROOMS,
    DEFAULT_CONFIG,
    SimulationState,
    apply_hvac_cooling,
    compute_next_temperature,
    decide_hvac,
    estimate_energy_kwh,
    generate_next_reading,
    summarize_rooms,
    validate_config_update,
)


# ---- HVAC rule -------------------------------------------------------------

def test_hvac_on_when_temperature_above_threshold():
    assert decide_hvac(26.1, 26.0) == "ON"
    assert decide_hvac(30.0, 26.0) == "ON"


def test_hvac_off_when_temperature_below_threshold():
    assert decide_hvac(25.9, 26.0) == "OFF"
    assert decide_hvac(20.0, 26.0) == "OFF"


def test_hvac_off_when_temperature_equals_threshold():
    assert decide_hvac(26.0, 26.0) == "OFF"


def test_hvac_follows_a_custom_threshold():
    assert decide_hvac(24.0, 23.0) == "ON"
    assert decide_hvac(24.0, 25.0) == "OFF"


# ---- Bounded HVAC cooling (deterministic, no random) ----------------------

def test_room_above_threshold_is_cooled_by_one_step():
    cooled = apply_hvac_cooling(27.0, 26.0, 0.3)
    assert cooled == 26.7
    assert compute_next_temperature(27.0, 26.0, 0.3, env_delta_c=5.0) == 26.7


def test_cooling_never_drives_temperature_below_threshold():
    assert apply_hvac_cooling(26.1, 26.0, 0.3) == 26.0
    assert apply_hvac_cooling(26.2, 26.0, 0.3) == 26.0
    assert apply_hvac_cooling(26.0, 26.0, 0.3) == 26.0
    assert apply_hvac_cooling(25.4, 26.0, 0.3) == 25.4
    assert apply_hvac_cooling(30.0, 26.0, 0.3) == 29.7


def test_hvac_off_when_temperature_at_or_below_threshold_after_step():
    config = dict(DEFAULT_CONFIG)
    config["temperature_noise_c"] = 0.0
    previous = {
        "temperature_c": 25.5,
        "humidity_pct": 45.0,
        "occupancy": 4,
        "hvac_status": "OFF",
    }
    reading = generate_next_reading(
        ROOMS[0], previous, config, random.Random(0), datetime(2026, 1, 1)
    )
    assert reading["temperature_c"] == 25.5
    assert reading["hvac_status"] == "OFF"
    assert reading["hvac_status"] == decide_hvac(
        reading["temperature_c"], config["temperature_threshold_c"]
    )


def test_room_state_persists_across_successive_steps():
    rng = random.Random(11)
    previous = {
        "temperature_c": 27.2,
        "humidity_pct": 48.0,
        "occupancy": 6,
        "hvac_status": "ON",
    }
    first = generate_next_reading(
        ROOMS[0], previous, DEFAULT_CONFIG, rng, datetime(2026, 1, 1, 12, 0, 0)
    )
    second = generate_next_reading(
        ROOMS[0], first, DEFAULT_CONFIG, rng, datetime(2026, 1, 1, 12, 0, 5)
    )
    assert first["temperature_c"] == 26.9
    assert first["hvac_status"] == "ON"
    assert abs(second["temperature_c"] - first["temperature_c"]) <= DEFAULT_CONFIG["cooling_rate_c"] + 1e-9
    assert second["occupancy"] >= first["occupancy"] - 2
    assert second["occupancy"] <= first["occupancy"] + 2


def test_generated_cooling_step_matches_threshold_rule():
    rng = random.Random(2)
    previous = {
        "temperature_c": 26.05,
        "humidity_pct": 50.0,
        "occupancy": 3,
        "hvac_status": "ON",
    }
    reading = generate_next_reading(
        ROOMS[0], previous, DEFAULT_CONFIG, rng, datetime(2026, 1, 1)
    )
    assert reading["temperature_c"] == 26.0
    assert reading["hvac_status"] == "OFF"
    assert reading["hvac_status"] == decide_hvac(
        reading["temperature_c"], DEFAULT_CONFIG["temperature_threshold_c"]
    )


# ---- Energy estimate -------------------------------------------------------

def test_energy_is_higher_when_hvac_is_on():
    off = estimate_energy_kwh(10, "OFF", 2.0, 15)
    on = estimate_energy_kwh(10, "ON", 2.0, 15)
    assert on > off


def test_energy_exact_value():
    # (0.3 + 0.05*10 + 2.0 kW) x 0.25 h = 2.8 x 0.25 = 0.7 kWh
    assert estimate_energy_kwh(10, "ON", 2.0, 15) == 0.7


# ---- Config validation -----------------------------------------------------

def test_valid_threshold_update_is_accepted():
    assert validate_config_update({"temperature_threshold_c": 24}) == {
        "temperature_threshold_c": 24.0
    }


@pytest.mark.parametrize(
    "bad_updates",
    [
        {"temperature_threshold_c": "hot"},
        {"temperature_threshold_c": True},
        {"temperature_threshold_c": 5},
        {"temperature_threshold_c": 99},
        {"interval_seconds": 0},
        {"interval_seconds": 2.5},
        {"unknown_setting": 1},
        {},
        [],
        "text",
    ],
)
def test_invalid_config_updates_are_rejected(bad_updates):
    with pytest.raises(ValueError):
        validate_config_update(bad_updates)


# ---- Summary ---------------------------------------------------------------

def test_summary_values():
    readings = [
        {"temperature_c": 24.0, "humidity_pct": 40.0, "occupancy": 5, "hvac_status": "OFF", "energy_kwh": 1.0},
        {"temperature_c": 28.0, "humidity_pct": 50.0, "occupancy": 10, "hvac_status": "ON", "energy_kwh": 2.0},
    ]
    summary = summarize_rooms(readings)
    assert summary["average_temperature_c"] == 26.0
    assert summary["average_humidity_pct"] == 45.0
    assert summary["total_occupancy"] == 15
    assert summary["total_energy_kwh"] == 3.0
    assert summary["rooms_with_hvac_on"] == 1


def test_summary_of_no_readings_does_not_crash():
    assert summarize_rooms([])["total_occupancy"] == 0


# ---- Seeded simulation (random but repeatable) -----------------------------

def test_same_seed_gives_same_readings():
    first = SimulationState(seed=7).step(datetime(2026, 1, 1, 12, 0, 0))
    second = SimulationState(seed=7).step(datetime(2026, 1, 1, 12, 0, 0))
    assert first == second


def test_generated_reading_has_all_fields_and_valid_ranges():
    rng = random.Random(1)
    previous = None
    for _ in range(200):
        reading = generate_next_reading(
            ROOMS[0], previous, DEFAULT_CONFIG, rng, datetime(2026, 1, 1)
        )
        assert set(reading) == {
            "timestamp", "room_id", "room_name", "temperature_c",
            "humidity_pct", "occupancy", "hvac_status", "energy_kwh",
        }
        assert DEFAULT_CONFIG["temperature_min_c"] <= reading["temperature_c"] <= DEFAULT_CONFIG["temperature_max_c"]
        assert DEFAULT_CONFIG["humidity_min_pct"] <= reading["humidity_pct"] <= DEFAULT_CONFIG["humidity_max_pct"]
        assert 0 <= reading["occupancy"] <= ROOMS[0]["max_occupancy"]
        # The HVAC status must always agree with the rule.
        assert reading["hvac_status"] == decide_hvac(
            reading["temperature_c"], DEFAULT_CONFIG["temperature_threshold_c"]
        )
        previous = reading


def test_changing_threshold_updates_latest_hvac_status():
    state = SimulationState(seed=3)
    state.step(datetime(2026, 1, 1))
    state.update_config({"temperature_threshold_c": 15})   # everything is hotter than 15
    assert all(r["hvac_status"] == "ON" for r in state.get_latest())
    state.update_config({"temperature_threshold_c": 40})   # nothing is hotter than 40
    assert all(r["hvac_status"] == "OFF" for r in state.get_latest())
