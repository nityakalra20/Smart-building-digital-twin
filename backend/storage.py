"""
storage.py - Saves and loads sensor readings using a CSV file.

CSV = "comma separated values": a plain text table. The first line holds the
column names and every other line is one reading of one room.
"""

import csv
import os
import threading

FIELDS = [
    "timestamp",
    "room_id",
    "room_name",
    "temperature_c",
    "humidity_pct",
    "occupancy",
    "hvac_status",
    "energy_kwh",
]


def _row_to_reading(row):
    """Convert a CSV row (all text) into a reading with proper types.

    Returns None if the row is damaged (missing values or text where a number
    should be), so one bad line never breaks the whole history.
    """
    try:
        if any(row.get(name) in (None, "") for name in FIELDS):
            return None
        status = row["hvac_status"].strip().upper()
        if status not in ("ON", "OFF"):
            return None
        return {
            "timestamp": row["timestamp"],
            "room_id": row["room_id"],
            "room_name": row["room_name"],
            "temperature_c": float(row["temperature_c"]),
            "humidity_pct": float(row["humidity_pct"]),
            "occupancy": int(row["occupancy"]),
            "hvac_status": status,
            "energy_kwh": float(row["energy_kwh"]),
        }
    except (ValueError, TypeError, AttributeError):
        return None


class CsvStorage:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        """Create the folder and a header-only file if needed (also fixes an empty file)."""
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        with self._lock:
            if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
                with open(self.path, "w", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=FIELDS).writeheader()

    def append(self, readings):
        """Add readings (a list of dicts) to the end of the file."""
        if not readings:
            return
        self._ensure_file()
        with self._lock:
            with open(self.path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                writer.writerows(readings)

    def read_all(self):
        """Return every valid reading in the file (oldest first)."""
        self._ensure_file()
        readings = []
        with self._lock:
            with open(self.path, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    reading = _row_to_reading(row)
                    if reading is not None:
                        readings.append(reading)
        return readings

    def read_latest_per_room(self):
        """Return the most recent saved reading of each room."""
        latest = {}
        for reading in self.read_all():
            latest[reading["room_id"]] = reading
        return list(latest.values())

    def read_history(self, limit_steps=60, room_id=None):
        """Return the most recent `limit_steps` time points.

        All rooms in one simulation step share the same timestamp, so we group
        by timestamp. Each point looks like:
            {"timestamp": ..., "total_energy_kwh": ..., "by_room": {room_id: kWh}}
        Also returns the matching raw readings.
        """
        readings = self.read_all()
        if room_id:
            readings = [r for r in readings if r["room_id"] == room_id]

        # Keep the order of first appearance of each timestamp.
        timestamps = []
        seen = set()
        for r in readings:
            if r["timestamp"] not in seen:
                seen.add(r["timestamp"])
                timestamps.append(r["timestamp"])
        keep = set(timestamps[-limit_steps:])
        readings = [r for r in readings if r["timestamp"] in keep]

        points = {}
        for r in readings:
            point = points.setdefault(
                r["timestamp"],
                {"timestamp": r["timestamp"], "total_energy_kwh": 0.0, "by_room": {}},
            )
            point["by_room"][r["room_id"]] = r["energy_kwh"]
            point["total_energy_kwh"] = round(point["total_energy_kwh"] + r["energy_kwh"], 3)

        series = [points[t] for t in timestamps if t in keep]
        return {"readings": readings, "energy_series": series}
