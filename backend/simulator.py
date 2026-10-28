"""
simulator.py - Simulated sensor data and rule-based HVAC logic.

IMPORTANT: Every value produced here is SIMULATED. Nothing comes from real
sensors. The file has two clearly separated parts:

  PART 1 - Deterministic logic (no randomness). These functions always give
           the same output for the same input, so they are easy to unit test.
              decide_hvac(), apply_hvac_cooling(), compute_next_temperature(),
              estimate_energy_kwh(), validate_config_update(), summarize_rooms()

  PART 2 - Random simulation. These functions use Python's `random` module.
           They accept a `random.Random` object, so a test can pass a seeded
           generator (e.g. random.Random(42)) and get repeatable numbers.
              environmental_delta(), generate_next_reading(), SimulationState
"""

import copy
import random
import threading
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The three simulated rooms. These numbers shape the simulated behaviour:
#   ambient_temp_c  - temperature the room drifts toward when HVAC is OFF
#   heat_per_person_c - extra degrees of heat each person adds to that target
#   max_occupancy   - capacity of the room
#   hvac_power_kw   - assumed electrical power of the room's HVAC when ON
ROOMS = [
    {
        "id": "room-101",
        "name": "Room 101",
        "ambient_temp_c": 27.5,
        "heat_per_person_c": 0.08,
        "max_occupancy": 30,
        "hvac_power_kw": 2.0,
    },
    {
        "id": "room-102",
        "name": "Room 102",
        "ambient_temp_c": 25.5,
        "heat_per_person_c": 0.08,
        "max_occupancy": 25,
        "hvac_power_kw": 1.8,
    },
    {
        "id": "conference-room",
        "name": "Conference Room",
        "ambient_temp_c": 26.5,
        "heat_per_person_c": 0.10,
        "max_occupancy": 20,
        "hvac_power_kw": 2.5,
    },
]

# Settings that can be tuned. Only `temperature_threshold_c` and
# `interval_seconds` can be changed at run time through the API.
DEFAULT_CONFIG = {
    "temperature_threshold_c": 26.0,   # HVAC turns ON above this value
    "interval_seconds": 5,             # real seconds between simulation steps
    "simulated_minutes_per_step": 15,  # building time each step represents
    "temperature_min_c": 18.0,         # simulation will never go below this
    "temperature_max_c": 34.0,         # simulation will never go above this
    "humidity_min_pct": 30.0,
    "humidity_max_pct": 70.0,
    "cooling_rate_c": 0.3,             # illustrative °C drop per step while cooling
    "temperature_noise_c": 0.3,        # size of random temperature wobble when HVAC is OFF
}

# Limits used when validating a configuration update.
THRESHOLD_MIN_C = 15.0
THRESHOLD_MAX_C = 40.0
INTERVAL_MIN_SECONDS = 1
INTERVAL_MAX_SECONDS = 3600

# Base electricity use of a room (lighting, sockets) and per person, in kW.
BASE_LOAD_KW = 0.3
PER_PERSON_LOAD_KW = 0.05


# ---------------------------------------------------------------------------
# PART 1 - Deterministic logic (easy to test)
# ---------------------------------------------------------------------------

def decide_hvac(temperature_c, threshold_c):
    """Rule-based HVAC control.

    Above the threshold -> "ON".  At or below the threshold -> "OFF".
    This is a software rule only; no physical HVAC is controlled.
    """
    if temperature_c > threshold_c:
        return "ON"
    return "OFF"


def apply_hvac_cooling(temperature_c, threshold_c, cooling_rate_c):
    """Illustrative bounded cooling toward the configured threshold.

    Subtracts the smaller of the cooling rate and the excess above the
    threshold, so cooling alone never drives the temperature below the
    target. This is a software model only; no physical HVAC is controlled.
    """
    excess = temperature_c - threshold_c
    if excess <= 0:
        return temperature_c
    return temperature_c - min(cooling_rate_c, excess)


def compute_next_temperature(previous_c, threshold_c, cooling_rate_c, env_delta_c=0.0):
    """Next room temperature from the previous value.

    Order is fixed so the reported temperature and HVAC rule stay consistent:
      1. If the previous temperature is above the threshold, apply cooling.
      2. Otherwise apply the supplied environmental change (tests can pass 0).
    Random sampling lives outside this function so cooling can be tested
    without the random module.
    """
    if previous_c > threshold_c:
        return apply_hvac_cooling(previous_c, threshold_c, cooling_rate_c)
    return previous_c + env_delta_c


def estimate_energy_kwh(occupancy, hvac_status, hvac_power_kw, minutes):
    """Estimate energy used by one room during one simulation step (kWh).

    power (kW) = base load + per-person load + HVAC power (only when ON)
    energy (kWh) = power (kW) x time (hours)
    """
    power_kw = BASE_LOAD_KW + PER_PERSON_LOAD_KW * occupancy
    if hvac_status == "ON":
        power_kw += hvac_power_kw
    return round(power_kw * (minutes / 60.0), 3)


def _is_number(value):
    """True for int/float, but not for bool (True/False are ints in Python)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_config_update(updates):
    """Check a dictionary of requested config changes.

    Returns a cleaned dictionary. Raises ValueError with a readable message if
    anything is invalid. Only two settings may be changed at run time.
    """
    if not isinstance(updates, dict) or not updates:
        raise ValueError("Request body must be a non-empty JSON object.")

    allowed = {"temperature_threshold_c", "interval_seconds"}
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(
            "Unknown or read-only setting(s): "
            + ", ".join(sorted(unknown))
            + ". Allowed: "
            + ", ".join(sorted(allowed))
            + "."
        )

    cleaned = {}

    if "temperature_threshold_c" in updates:
        value = updates["temperature_threshold_c"]
        if not _is_number(value):
            raise ValueError("temperature_threshold_c must be a number.")
        if not THRESHOLD_MIN_C <= value <= THRESHOLD_MAX_C:
            raise ValueError(
                f"temperature_threshold_c must be between {THRESHOLD_MIN_C} "
                f"and {THRESHOLD_MAX_C}."
            )
        cleaned["temperature_threshold_c"] = float(value)

    if "interval_seconds" in updates:
        value = updates["interval_seconds"]
        if not _is_number(value) or int(value) != value:
            raise ValueError("interval_seconds must be a whole number.")
        if not INTERVAL_MIN_SECONDS <= value <= INTERVAL_MAX_SECONDS:
            raise ValueError(
                f"interval_seconds must be between {INTERVAL_MIN_SECONDS} "
                f"and {INTERVAL_MAX_SECONDS}."
            )
        cleaned["interval_seconds"] = int(value)

    return cleaned


def summarize_rooms(readings):
    """Building-wide numbers for the dashboard summary cards."""
    if not readings:
        return {
            "average_temperature_c": None,
            "average_humidity_pct": None,
            "total_occupancy": 0,
            "total_energy_kwh": 0.0,
            "rooms_with_hvac_on": 0,
        }
    count = len(readings)
    return {
        "average_temperature_c": round(
            sum(r["temperature_c"] for r in readings) / count, 1
        ),
        "average_humidity_pct": round(
            sum(r["humidity_pct"] for r in readings) / count, 1
        ),
        "total_occupancy": sum(r["occupancy"] for r in readings),
        "total_energy_kwh": round(sum(r["energy_kwh"] for r in readings), 3),
        "rooms_with_hvac_on": sum(1 for r in readings if r["hvac_status"] == "ON"),
    }


def _clamp(value, low, high):
    return max(low, min(high, value))


# ---------------------------------------------------------------------------
# PART 2 - Random simulation
# ---------------------------------------------------------------------------

def environmental_delta(config, rng):
    """Small random temperature change used only when simulated HVAC is OFF."""
    return rng.uniform(-config["temperature_noise_c"], config["temperature_noise_c"])


def generate_next_reading(room, previous, config, rng, timestamp):
    """Create one SIMULATED reading for one room.

    room      - one dictionary from ROOMS
    previous  - the room's previous reading (dict), or None for the first one
    config    - settings dictionary (see DEFAULT_CONFIG)
    rng       - a random.Random object (seed it in tests for repeatable output)
    timestamp - datetime for this reading

    Temperature is carried forward from the previous step. If it is above the
    threshold, bounded cooling is applied. If it is at or below the threshold,
    a small environmental fluctuation is applied instead. HVAC status is then
    decided from the new temperature so the reading and the rule agree.
    """
    # 1. Occupancy: small random change from last time, within 0..capacity.
    if previous is None:
        occupancy = rng.randint(0, room["max_occupancy"] // 2)
    else:
        change = rng.choice([-2, -1, 0, 0, 1, 2])
        occupancy = _clamp(previous["occupancy"] + change, 0, room["max_occupancy"])

    # 2. Temperature: keep the previous value, then cool or apply a small wobble.
    threshold = config["temperature_threshold_c"]
    if previous is None:
        temperature = room["ambient_temp_c"] + room["heat_per_person_c"] * occupancy
        temperature = _clamp(temperature, config["temperature_min_c"], config["temperature_max_c"])
    else:
        temperature = previous["temperature_c"]

    env_delta = 0.0
    if temperature <= threshold:
        env_delta = environmental_delta(config, rng)
    temperature = compute_next_temperature(
        temperature, threshold, config["cooling_rate_c"], env_delta
    )
    temperature = _clamp(temperature, config["temperature_min_c"], config["temperature_max_c"])
    temperature = round(temperature, 1)

    # 3. Humidity: drifts toward a target that rises with occupancy and
    #    falls when the HVAC is running.
    humidity_target = 48.0 + 0.3 * occupancy
    if previous is not None and previous["hvac_status"] == "ON":
        humidity_target -= 4.0
    previous_humidity = previous["humidity_pct"] if previous else humidity_target
    humidity = previous_humidity + (humidity_target - previous_humidity) * 0.3 + rng.uniform(-1.0, 1.0)
    humidity = round(_clamp(humidity, config["humidity_min_pct"], config["humidity_max_pct"]), 1)

    # 4. Apply the rule-based HVAC control, then estimate energy.
    hvac_status = decide_hvac(temperature, threshold)
    energy = estimate_energy_kwh(
        occupancy, hvac_status, room["hvac_power_kw"], config["simulated_minutes_per_step"]
    )

    return {
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "room_id": room["id"],
        "room_name": room["name"],
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "occupancy": int(occupancy),
        "hvac_status": hvac_status,
        "energy_kwh": energy,
    }


class SimulationState:
    """Holds the current config and the latest reading of every room.

    A lock makes it safe for the background thread and API requests to use
    the same object at the same time.
    """

    def __init__(self, seed=None, config=None):
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        if config:
            self.config.update(config)
        self.rng = random.Random(seed)
        self.latest = {}  # room_id -> latest reading dict
        self.lock = threading.RLock()

    def restore(self, readings):
        """Load previously saved readings (e.g. from CSV) as the starting point."""
        with self.lock:
            for reading in readings:
                self.latest[reading["room_id"]] = dict(reading)

    def step(self, timestamp=None):
        """Run one simulation cycle: one new reading for every room."""
        timestamp = timestamp or datetime.now()
        with self.lock:
            new_readings = []
            for room in ROOMS:
                reading = generate_next_reading(
                    room, self.latest.get(room["id"]), self.config, self.rng, timestamp
                )
                self.latest[room["id"]] = reading
                new_readings.append(dict(reading))
            return new_readings

    def get_latest(self):
        """Latest reading per room, in the fixed ROOMS order."""
        with self.lock:
            return [dict(self.latest[r["id"]]) for r in ROOMS if r["id"] in self.latest]

    def get_config(self):
        with self.lock:
            return dict(self.config)

    def update_config(self, updates):
        """Validate and apply a config change. Raises ValueError if invalid.

        If the threshold changes, the HVAC status of the *latest* readings is
        re-evaluated so the dashboard immediately follows the new rule.
        """
        cleaned = validate_config_update(updates)
        with self.lock:
            self.config.update(cleaned)
            if "temperature_threshold_c" in cleaned:
                rooms_by_id = {r["id"]: r for r in ROOMS}
                for room_id, reading in self.latest.items():
                    reading["hvac_status"] = decide_hvac(
                        reading["temperature_c"], self.config["temperature_threshold_c"]
                    )
                    reading["energy_kwh"] = estimate_energy_kwh(
                        reading["occupancy"],
                        reading["hvac_status"],
                        rooms_by_id[room_id]["hvac_power_kw"],
                        self.config["simulated_minutes_per_step"],
                    )
            return dict(self.config)

    def make_seed_history(self, steps, end_time=None):
        """Create `steps` past readings so the dashboard is not empty on first run.

        Timestamps are spaced `interval_seconds` apart and end at `end_time`.
        Returns a flat list of readings (3 per step).
        """
        end_time = end_time or datetime.now()
        interval = timedelta(seconds=self.config["interval_seconds"])
        history = []
        for i in range(steps):
            moment = end_time - interval * (steps - 1 - i)
            history.extend(self.step(moment))
        return history
