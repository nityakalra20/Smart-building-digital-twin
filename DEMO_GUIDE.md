# Demonstration Guide (3–5 minutes)

## Before the evaluation (do this 10 minutes earlier)

1. Terminal 1: `cd backend`, activate the virtual environment, run `python app.py`.
2. Terminal 2: `cd frontend`, run `npm run dev`.
3. Open http://localhost:5173 and confirm the dashboard is loading and says "Backend connected".
4. In a third terminal (backend folder, virtual environment active) run `python -m pytest -v` once, so you know the tests pass on your machine.
5. Keep `data/sensor_readings.csv` open in a text editor or Excel.
6. Have this backup: if the live demo fails, show `docs/dashboard.png` and the test output.

## Script

| Time | What to do | What to say |
|---|---|---|
| 0:00–0:30 | Show the header and the yellow **Simulated Sensor Data** badge | "This is a digital twin: a software model of three rooms that mirrors a building's state. There is no real hardware, so the backend simulates the sensors, and the dashboard says so clearly." |
| 0:30–1:15 | Point at the summary cards, then the three room cards. Wait for the numbers to change | "Flask generates a new reading for every room each 5 seconds. React asks the API for the latest data and updates the screen. You can see temperature, humidity, occupancy, HVAC status and an energy estimate." |
| 1:15–1:45 | Show the floor view and the Alerts panel | "Colours show the room condition: green is comfortable, amber is within 1 °C of the threshold, red is above it. Any room above the threshold appears in the Alerts panel." |
| 1:45–2:45 | Type **15** in the threshold box and press **Apply**. Then set **35**. Then set **26** again | "The HVAC rule is simple: above the threshold the HVAC is ON, at or below it is OFF. At 15 °C every room is above it, so all three alerts and HVAC ON appear. At 35 °C nothing is. This is only a software rule; no physical HVAC is controlled." |
| 2:45–3:15 | Enter **99** and press **Apply** | "The backend validates input and rejects values outside 15–40 °C, and the frontend displays the error." |
| 3:15–3:45 | Scroll to the energy chart. Press **Run one simulation step** | "The chart is built from the saved CSV history. Each step adds a new point." Switch to the CSV file and show the new rows at the bottom. |
| 3:45–4:15 | Open http://127.0.0.1:5001/api/rooms in a new browser tab | "This is the REST API returning JSON; the dashboard is just one client of it." |
| 4:15–4:45 | Show the terminal with the pytest result (`48 passed`) | "The HVAC rule is a pure function, so it is tested deterministically. The tests also cover the API, validation and CSV handling." |
| 4:45–5:00 | Optional: stop the backend and show the red error banner | "If the backend is down the dashboard shows a clear message and keeps the last data." Restart the backend before taking questions. |

## Be ready to say honestly

- Values are simulated, not measured.
- The simulation is simplified: rooms do not affect each other, and there is no outdoor weather.
- The HVAC rule is basic on/off logic without hysteresis.
- The React front end has no automated tests of its own; the backend does.

## If something goes wrong

| Problem | Quick fix |
|---|---|
| Dashboard shows "Cannot reach the backend" | Terminal 1 is not running; start `python app.py` |
| Port 5173 already used | Close the old `npm run dev` terminal and run it again |
| Port 5001 already used | Close the old backend, or change the port at the bottom of `app.py` and in `frontend/.env` |
| Chart is empty | Press **Run one simulation step** a few times, or delete `data/sensor_readings.csv` and restart the backend |
