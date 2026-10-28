"""CSV storage tests: normal use plus missing / empty / damaged files."""

from app import create_app
from storage import CsvStorage, FIELDS


def make_reading(timestamp="2026-01-01T10:00:00", room_id="room-101", energy=1.0):
    return {
        "timestamp": timestamp,
        "room_id": room_id,
        "room_name": "Room 101",
        "temperature_c": 25.0,
        "humidity_pct": 45.0,
        "occupancy": 4,
        "hvac_status": "OFF",
        "energy_kwh": energy,
    }


def test_missing_file_is_created_with_header(tmp_path):
    path = tmp_path / "new_folder" / "readings.csv"
    storage = CsvStorage(str(path))
    assert path.exists()
    assert path.read_text().strip() == ",".join(FIELDS)
    assert storage.read_all() == []


def test_empty_file_is_handled(tmp_path):
    path = tmp_path / "readings.csv"
    path.write_text("")
    storage = CsvStorage(str(path))
    assert storage.read_all() == []
    assert storage.read_history()["energy_series"] == []


def test_append_then_read_round_trip(tmp_path):
    storage = CsvStorage(str(tmp_path / "readings.csv"))
    storage.append([make_reading()])
    rows = storage.read_all()
    assert len(rows) == 1
    assert rows[0]["temperature_c"] == 25.0
    assert rows[0]["occupancy"] == 4


def test_damaged_rows_are_skipped(tmp_path):
    path = tmp_path / "readings.csv"
    path.write_text(
        ",".join(FIELDS) + "\n"
        "2026-01-01T10:00:00,room-101,Room 101,25.0,45.0,4,OFF,1.0\n"
        "2026-01-01T10:00:05,room-101,Room 101,not-a-number,45.0,4,OFF,1.0\n"
        "2026-01-01T10:00:10,room-101,Room 101,25.0,45.0,4,MAYBE,1.0\n"
        "broken line\n"
    )
    rows = CsvStorage(str(path)).read_all()
    assert len(rows) == 1


def test_history_groups_rooms_by_timestamp_and_sums_energy(tmp_path):
    storage = CsvStorage(str(tmp_path / "readings.csv"))
    storage.append([
        make_reading("t1", "room-101", 1.0),
        make_reading("t1", "room-102", 2.0),
        make_reading("t2", "room-101", 3.0),
    ])
    series = storage.read_history(limit_steps=10)["energy_series"]
    assert [p["timestamp"] for p in series] == ["t1", "t2"]
    assert series[0]["total_energy_kwh"] == 3.0
    assert series[1]["by_room"] == {"room-101": 3.0}


def test_app_starts_with_an_empty_csv_and_creates_seed_data(tmp_path):
    path = tmp_path / "readings.csv"
    path.write_text("")
    app = create_app(csv_path=str(path), seed=1)
    data = app.test_client().get("/api/rooms").get_json()["data"]
    assert len(data["rooms"]) == 3


def test_app_restarts_from_saved_csv_without_new_seed_data(tmp_path):
    path = str(tmp_path / "readings.csv")
    create_app(csv_path=path, seed=1)
    rows_after_first_start = len(CsvStorage(path).read_all())
    create_app(csv_path=path, seed=2)   # second start must not add seed data again
    assert len(CsvStorage(path).read_all()) == rows_after_first_start


def test_background_loop_only_starts_once(tmp_path):
    app = create_app(csv_path=str(tmp_path / "r.csv"), seed=1, start_background=False)
    loop = app.config["SIMULATOR_LOOP"]
    loop.start()
    first_thread = loop._thread
    loop.start()   # second call must be ignored
    assert loop._thread is first_thread
    loop.stop()
