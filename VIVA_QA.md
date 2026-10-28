# Viva Preparation: Questions and Answers

Answers are written so you can say them in your own words. Where it helps, they point to the file in this project.

---

**1. What is a digital twin?**
A digital twin is a virtual model of a real object, building or system that mirrors its state using data. It lets you monitor it, test rules and predict problems without touching the real thing. In this project the "twin" is a software model of three rooms, with the state shown on a dashboard.

**2. Why did you use simulated data?**
I do not have physical IoT sensors or access to real building data. Simulation lets me develop, test and demonstrate the complete software pipeline. The data is clearly labelled as simulated everywhere (dashboard badge, API field `data_source`). Real sensors could later replace the simulator without changing the rest of the system.

**3. How does the simulator work?**
`simulator.py` creates a new reading for each room from the previous one. Occupancy changes by a small random amount. Temperature drifts toward the room's ambient value (higher with more people) when HVAC is off, and falls 0.5 °C per step when HVAC is on, plus a little random noise. Humidity follows a similar drift. Then the HVAC rule is applied and energy is estimated. It uses Python's `random` module. In tests I pass a seeded generator, so results repeat.

**4. Why separate the HVAC rule from the random code?**
The rule `decide_hvac()` is a pure function with no randomness, so the same input always gives the same output. That makes tests reliable. Random behaviour lives in a different function that accepts a seeded random generator.

**5. What does Flask do in this project?**
Flask is a Python web framework. It receives HTTP requests from the dashboard, calls my Python logic, and returns JSON. It also runs the background thread that creates readings every 5 seconds.

**6. What are a REST API and JSON?**
A REST API lets programs communicate over HTTP using URLs and methods: GET to read, POST to create or trigger, PUT to update. JSON is a text format for data made of keys and values, for example `{"temperature_c": 25.7}`. Both Python and JavaScript can read it easily. All my responses have the form `{"success": true, "data": ...}` or `{"success": false, "error": ...}`.

**7. How does React receive and display the data?**
`api.js` uses `fetch()` to call `/api/rooms` and `/api/history`. `App.jsx` stores the result in state with `useState`. When state changes React re-renders the components (summary cards, room cards, chart). A `setInterval` inside `useEffect` repeats the fetch every 5 seconds, and it is cleaned up when the page closes.

**8. What is CORS and why is Flask-CORS used?**
Browsers block a page from one origin (localhost:5173) calling a server on another origin (localhost:5001) unless the server allows it. Flask-CORS adds the permission headers for my frontend's origin.

**9. How does the HVAC threshold logic work?**
If temperature is greater than the threshold (default 26 °C), HVAC is ON. If it is equal to or below, HVAC is OFF. The threshold can be changed from the dashboard (`PUT /api/config`), and the latest readings update immediately. It is a software rule only; no physical HVAC is controlled.

**10. How does CSV storage work?**
Each reading is one line in `data/sensor_readings.csv` with columns: timestamp, room_id, room_name, temperature_c, humidity_pct, occupancy, hvac_status, energy_kwh. `storage.py` appends new rows and reads them back. If the file is missing or empty, it creates the header. Damaged lines are skipped so one bad line does not crash the app. A lock prevents two threads writing at once.

**11. How is the historical chart generated?**
`GET /api/history` reads the CSV, groups readings by timestamp, takes the latest 60 time points and adds up the three rooms' energy. React receives this as `energy_series` and draws a Recharts line chart with a total line and one line per room.

**12. How are alerts generated?**
In `AlertPanel.jsx`, any room whose temperature is above the threshold gets an alert showing how many degrees above it is. The backend also provides an `exceeds_threshold` flag for each room. If no room exceeds it, the panel shows an all-clear message.

**13. How is the energy estimate calculated?**
Power (kW) = 0.3 base load + 0.05 × people + HVAC power when ON. Energy (kWh) = power × 0.25 hours, because each step represents 15 simulated minutes. The numbers are assumptions for the simulation, not measurements.

**14. How did you avoid running two simulation loops?**
`BackgroundSimulator` has a `_started` flag so `start()` only works once, and `python app.py` runs Flask with `use_reloader=False`. The Flask auto-reloader would otherwise start a second copy of the program. A test checks the flag.

**15. How was the system tested?**
With pytest: 48 tests covering the HVAC rule (above, below and equal to the threshold), energy calculation, config validation, all API endpoints, error responses, and CSV handling for missing, empty and damaged files. Random parts use a fixed seed. I also ran the real servers and checked the dashboard in a browser. (Run `python -m pytest -v` to show it live.)

**16. What happens if the backend is not running?**
`api.js` catches the failed request and the dashboard shows a red banner with a helpful message. It keeps showing the last data and reconnects automatically at the next refresh.

**17. What are the current limitations?**
Simulated data only; rooms do not influence each other; no outdoor weather; simple on/off rule without hysteresis; CSV is not suitable for large data; polling instead of live push; config changes are not saved after a restart; Flask's development server is not for production; the front end has no automated tests.

**18. What would you improve next?**
Connect real sensors (for example MQTT), use a database, add hysteresis or a PID controller, model heat flow between rooms and weather, add WebSockets, add more rooms or a floor plan, and later add forecasting with machine learning.

**19. Why Vite instead of Create React App?**
Vite starts faster, needs little configuration and is the commonly recommended way to start a React project today.

**20. Why does the HVAC status sometimes flip between steps?**
Because the rule has no hysteresis. When a room is just above 26 °C, HVAC turns on and cools it by about 0.5 °C, so it falls under the threshold and the HVAC turns off again. A real controller would use a dead band, for example ON above 26 °C and OFF below 25 °C.

---

### Tip for the viva
If you are asked something you do not know, explain what you do know and say how you would find out. Be honest about what is simulated and what has and has not been tested.
