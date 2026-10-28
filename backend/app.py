"""
app.py - Flask backend (REST API) for the Smart Building Digital Twin.

Run it with:   python app.py
It serves JSON on http://localhost:5001 and, in the background, creates a new
SIMULATED reading for each room every few seconds and saves it to a CSV file.

Every response uses the same JSON shape:
    success:  {"success": true,  "data": {...}}
    failure:  {"success": false, "error": {"code": "...", "message": "..."}}
"""

import os
import threading
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from simulator import SimulationState, ROOMS, summarize_rooms
from storage import CsvStorage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "..", "data", "sensor_readings.csv")

SEED_HISTORY_STEPS = 30       # readings created on first start
MAX_STEPS_PER_REQUEST = 50    # limit for POST /api/simulation/step
MAX_HISTORY_LIMIT = 1000


# ---------------------------------------------------------------------------
# Small helpers for consistent JSON responses
# ---------------------------------------------------------------------------

def ok(data, status=200):
    return jsonify({"success": True, "data": data}), status


def fail(code, message, status):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


# ---------------------------------------------------------------------------
# Background simulation loop
# ---------------------------------------------------------------------------

class BackgroundSimulator:
    """Calls `run_step()` every `interval_seconds` in a separate thread.

    `_started` makes sure only ONE loop exists per object, so the simulation
    is never duplicated.
    """

    def __init__(self, run_step, get_interval):
        self._run_step = run_step
        self._get_interval = get_interval
        self._stop_event = threading.Event()
        self._thread = None
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._loop, name="simulator", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _loop(self):
        # wait() returns True when stop() was called, otherwise after the interval.
        while not self._stop_event.wait(self._get_interval()):
            try:
                self._run_step()
            except Exception as error:  # keep the loop alive whatever happens
                print(f"[simulator] step failed: {error}")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(csv_path=None, seed=None, start_background=False, seed_history=True):
    """Build the Flask app.

    Tests call create_app(csv_path=<temp file>, seed=1) so they get their own
    file and repeatable numbers, with no background thread.
    """
    app = Flask(__name__)

    allowed_origins = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    storage = CsvStorage(csv_path or DEFAULT_CSV_PATH)
    state = SimulationState(seed=seed)
    step_lock = threading.Lock()  # one simulation step (and CSV write) at a time

    # --- start-up data: continue from the CSV, or create an initial dataset ---
    saved_latest = storage.read_latest_per_room()
    if saved_latest:
        state.restore(saved_latest)
    elif seed_history:
        storage.append(state.make_seed_history(SEED_HISTORY_STEPS))

    def run_step():
        """One simulation cycle: generate readings and save them to the CSV."""
        with step_lock:
            readings = state.step(datetime.now())
            storage.append(readings)
            return readings

    app.config["STATE"] = state
    app.config["STORAGE"] = storage

    simulator_loop = BackgroundSimulator(
        run_step, lambda: state.get_config()["interval_seconds"]
    )
    app.config["SIMULATOR_LOOP"] = simulator_loop
    if start_background:
        simulator_loop.start()

    # --- helper that builds the "rooms" payload ---

    def build_rooms_payload():
        config = state.get_config()
        threshold = config["temperature_threshold_c"]
        rooms = []
        for reading in state.get_latest():
            room = dict(reading)
            room["exceeds_threshold"] = reading["temperature_c"] > threshold
            rooms.append(room)
        last_updated = max((r["timestamp"] for r in rooms), default=None)
        return {
            "rooms": rooms,
            "summary": summarize_rooms(rooms),
            "temperature_threshold_c": threshold,
            "last_updated": last_updated,
            "data_source": "simulated",
        }

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    @app.get("/api/health")
    def health():
        return ok(
            {
                "status": "ok",
                "service": "smart-building-digital-twin",
                "data_source": "simulated",
                "server_time": datetime.now().isoformat(timespec="seconds"),
            }
        )

    @app.get("/api/rooms")
    def get_rooms():
        return ok(build_rooms_payload())

    @app.get("/api/history")
    def get_history():
        # ?limit=<number of recent time points>   ?room_id=<id>
        limit_text = request.args.get("limit", "60")
        try:
            limit = int(limit_text)
        except ValueError:
            return fail("INVALID_LIMIT", "limit must be a whole number.", 400)
        if not 1 <= limit <= MAX_HISTORY_LIMIT:
            return fail(
                "INVALID_LIMIT", f"limit must be between 1 and {MAX_HISTORY_LIMIT}.", 400
            )

        room_id = request.args.get("room_id")
        if room_id and room_id not in {r["id"] for r in ROOMS}:
            return fail("UNKNOWN_ROOM", f"Unknown room_id '{room_id}'.", 404)

        history = storage.read_history(limit_steps=limit, room_id=room_id)
        history["count"] = len(history["readings"])
        return ok(history)

    @app.post("/api/simulation/step")
    def simulation_step():
        # Optional JSON body: {"steps": 3}  (default 1)
        steps = 1
        if request.data:
            body = request.get_json(silent=True)
            if not isinstance(body, dict):
                return fail("INVALID_JSON", "Body must be a JSON object.", 400)
            steps = body.get("steps", 1)
            if isinstance(steps, bool) or not isinstance(steps, int):
                return fail("INVALID_STEPS", "steps must be a whole number.", 400)
            if not 1 <= steps <= MAX_STEPS_PER_REQUEST:
                return fail(
                    "INVALID_STEPS",
                    f"steps must be between 1 and {MAX_STEPS_PER_REQUEST}.",
                    400,
                )

        new_readings = []
        for _ in range(steps):
            new_readings = run_step()
        payload = build_rooms_payload()
        payload["steps_run"] = steps
        return ok(payload, 201)

    @app.get("/api/config")
    def get_config():
        return ok(
            {
                "config": state.get_config(),
                "rooms": [
                    {"id": r["id"], "name": r["name"], "max_occupancy": r["max_occupancy"]}
                    for r in ROOMS
                ],
                "data_source": "simulated",
            }
        )

    @app.put("/api/config")
    def update_config():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return fail("INVALID_JSON", "Body must be a JSON object.", 400)
        try:
            config = state.update_config(body)
        except ValueError as error:
            return fail("INVALID_CONFIG", str(error), 400)
        return ok({"config": config})

    # ------------------------------------------------------------------
    # Error handlers: always answer with JSON, never an HTML error page
    # ------------------------------------------------------------------

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return fail(error.name.upper().replace(" ", "_"), error.description, error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        print(f"[server] unexpected error: {error}")
        return fail("INTERNAL_ERROR", "Something went wrong on the server.", 500)

    return app


if __name__ == "__main__":
    application = create_app(start_background=True)
    # use_reloader=False => the file watcher does not start a second copy of the
    # program, so only ONE background simulation loop ever runs.
    application.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)
