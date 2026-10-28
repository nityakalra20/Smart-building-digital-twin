"""API tests using Flask's built-in test client (no real server needed)."""

EXPECTED_ROOM_FIELDS = {
    "timestamp", "room_id", "room_name", "temperature_c", "humidity_pct",
    "occupancy", "hvac_status", "energy_kwh", "exceeds_threshold",
}


# ---- Health ----------------------------------------------------------------

def test_health_endpoint_responds_ok(client):
    response = client.get("/api/health")
    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


# ---- Rooms -----------------------------------------------------------------

def test_rooms_endpoint_returns_three_expected_rooms(client):
    response = client.get("/api/rooms")
    body = response.get_json()
    assert response.status_code == 200
    rooms = body["data"]["rooms"]
    assert [r["room_name"] for r in rooms] == ["Room 101", "Room 102", "Conference Room"]
    for room in rooms:
        assert set(room) == EXPECTED_ROOM_FIELDS
        assert room["hvac_status"] in ("ON", "OFF")
        assert isinstance(room["temperature_c"], float)
        assert isinstance(room["occupancy"], int)
    assert body["data"]["data_source"] == "simulated"
    assert body["data"]["temperature_threshold_c"] == 26.0
    assert "summary" in body["data"]


def test_rooms_hvac_matches_threshold_rule(client):
    rooms = client.get("/api/rooms").get_json()["data"]["rooms"]
    for room in rooms:
        expected = "ON" if room["temperature_c"] > 26.0 else "OFF"
        assert room["hvac_status"] == expected
        assert room["exceeds_threshold"] == (room["temperature_c"] > 26.0)


# ---- Simulation step -------------------------------------------------------

def test_simulation_step_adds_rows_to_history(client):
    before = client.get("/api/history?limit=1000").get_json()["data"]["count"]
    response = client.post("/api/simulation/step")
    assert response.status_code == 201
    after = client.get("/api/history?limit=1000").get_json()["data"]["count"]
    assert after == before + 3  # one new reading for each of the 3 rooms


def test_simulation_step_accepts_multiple_steps(client):
    before = client.get("/api/history?limit=1000").get_json()["data"]["count"]
    response = client.post("/api/simulation/step", json={"steps": 4})
    assert response.status_code == 201
    assert response.get_json()["data"]["steps_run"] == 4
    after = client.get("/api/history?limit=1000").get_json()["data"]["count"]
    assert after == before + 12


def test_simulation_step_rejects_invalid_steps(client):
    for bad in (0, -1, 1000, "three", 2.5, True):
        response = client.post("/api/simulation/step", json={"steps": bad})
        assert response.status_code == 400, bad
        assert response.get_json()["success"] is False


def test_simulation_step_rejects_non_object_body(client):
    response = client.post("/api/simulation/step", data="not json", content_type="application/json")
    assert response.status_code == 400


def test_simulation_step_returns_updated_readings(client):
    before_rooms = client.get("/api/rooms").get_json()["data"]["rooms"]
    response = client.post("/api/simulation/step")
    assert response.status_code == 201
    after = response.get_json()["data"]
    assert after["steps_run"] == 1
    rooms = after["rooms"]
    assert [r["room_name"] for r in rooms] == ["Room 101", "Room 102", "Conference Room"]
    for room in rooms:
        expected = "ON" if room["temperature_c"] > after["temperature_threshold_c"] else "OFF"
        assert room["hvac_status"] == expected
    assert rooms == client.get("/api/rooms").get_json()["data"]["rooms"]
    before_by_id = {r["room_id"]: r for r in before_rooms}
    changed = any(
        before_by_id[r["room_id"]]["temperature_c"] != r["temperature_c"]
        or before_by_id[r["room_id"]]["occupancy"] != r["occupancy"]
        or before_by_id[r["room_id"]]["humidity_pct"] != r["humidity_pct"]
        or before_by_id[r["room_id"]]["energy_kwh"] != r["energy_kwh"]
        for r in rooms
    )
    assert changed


def test_simulation_step_saves_new_readings_in_csv_history(client):
    step = client.post("/api/simulation/step").get_json()["data"]
    history = client.get("/api/history?limit=1").get_json()["data"]
    latest_by_room = {r["room_id"]: r for r in history["readings"]}
    for room in step["rooms"]:
        saved = latest_by_room[room["room_id"]]
        assert saved["timestamp"] == room["timestamp"]
        assert saved["temperature_c"] == room["temperature_c"]
        assert saved["hvac_status"] == room["hvac_status"]
        assert saved["occupancy"] == room["occupancy"]


# ---- History ---------------------------------------------------------------

def test_history_has_seed_data_and_energy_series(client):
    data = client.get("/api/history").get_json()["data"]
    assert data["count"] > 0
    assert len(data["energy_series"]) > 0
    point = data["energy_series"][0]
    assert {"timestamp", "total_energy_kwh", "by_room"} <= set(point)


def test_history_limit_is_applied(client):
    data = client.get("/api/history?limit=5").get_json()["data"]
    assert len(data["energy_series"]) == 5
    assert data["count"] == 15


def test_history_rejects_invalid_limit(client):
    for bad in ("abc", "0", "-3", "100000"):
        response = client.get(f"/api/history?limit={bad}")
        assert response.status_code == 400, bad


def test_history_unknown_room_returns_404(client):
    response = client.get("/api/history?room_id=nonexistent")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "UNKNOWN_ROOM"


def test_history_can_filter_by_room(client):
    data = client.get("/api/history?room_id=room-101").get_json()["data"]
    assert {r["room_id"] for r in data["readings"]} == {"room-101"}


# ---- Config ----------------------------------------------------------------

def test_get_config_returns_threshold(client):
    data = client.get("/api/config").get_json()["data"]
    assert data["config"]["temperature_threshold_c"] == 26.0
    assert data["config"]["interval_seconds"] == 5
    assert data["config"]["cooling_rate_c"] == 0.3


def test_put_config_changes_threshold_and_rooms_follow(client):
    response = client.put("/api/config", json={"temperature_threshold_c": 15})
    assert response.status_code == 200
    rooms = client.get("/api/rooms").get_json()["data"]["rooms"]
    assert all(r["hvac_status"] == "ON" for r in rooms)

    client.put("/api/config", json={"temperature_threshold_c": 40})
    rooms = client.get("/api/rooms").get_json()["data"]["rooms"]
    assert all(r["hvac_status"] == "OFF" for r in rooms)


def test_put_config_rejects_invalid_values(client):
    bad_bodies = [
        {"temperature_threshold_c": "hot"},
        {"temperature_threshold_c": 500},
        {"interval_seconds": -5},
        {"nonsense": 1},
        {},
    ]
    for body in bad_bodies:
        response = client.put("/api/config", json=body)
        assert response.status_code == 400, body
        assert response.get_json()["error"]["code"] == "INVALID_CONFIG"


def test_put_config_rejects_non_json(client):
    response = client.put("/api/config", data="hello", content_type="text/plain")
    assert response.status_code == 400


# ---- Errors ----------------------------------------------------------------

def test_unknown_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_wrong_method_returns_json_405(client):
    response = client.post("/api/health")
    assert response.status_code == 405
    assert response.get_json()["success"] is False
