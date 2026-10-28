import { useCallback, useEffect, useRef, useState } from "react";
import Header from "./components/Header.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import RoomCard from "./components/RoomCard.jsx";
import BuildingMap from "./components/BuildingMap.jsx";
import AlertPanel from "./components/AlertPanel.jsx";
import EnergyChart from "./components/EnergyChart.jsx";
import Controls from "./components/Controls.jsx";
import { getHistory, getRooms, runSimulationStep, updateThreshold } from "./services/api.js";

// How often the dashboard asks the backend for new data (milliseconds).
const REFRESH_INTERVAL_MS = 5000;

export default function App() {
  const [roomsData, setRoomsData] = useState(null); // response of GET /api/rooms
  const [history, setHistory] = useState(null);     // response of GET /api/history
  const [loading, setLoading] = useState(true);     // true until the first load finishes
  const [error, setError] = useState(null);         // text of the latest error, or null
  const [fetchedAt, setFetchedAt] = useState(null); // when the browser last got data
  const isMounted = useRef(true);

  // Fetch rooms and history together. Keeps the old data on screen if it fails.
  const loadData = useCallback(async () => {
    try {
      const [rooms, hist] = await Promise.all([getRooms(), getHistory(60)]);
      if (!isMounted.current) return;
      setRoomsData(rooms);
      setHistory(hist);
      setFetchedAt(new Date());
      setError(null);
    } catch (err) {
      if (!isMounted.current) return;
      setError(err.message);
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, []);

  // Load once on start, then again every REFRESH_INTERVAL_MS.
  useEffect(() => {
    isMounted.current = true;
    loadData();
    const timer = setInterval(loadData, REFRESH_INTERVAL_MS);
    return () => {
      isMounted.current = false;
      clearInterval(timer);
    };
  }, [loadData]);

  // Button handlers. Each one calls the backend, then reloads the dashboard.
  async function handleStep() {
    try {
      await runSimulationStep();
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleThresholdChange(value) {
    // Errors are thrown back to the Controls component so it can show them.
    await updateThreshold(value);
    await loadData();
  }

  const rooms = roomsData?.rooms ?? [];
  const threshold = roomsData?.temperature_threshold_c ?? 26;

  return (
    <div className="app">
      <Header lastUpdated={roomsData?.last_updated} fetchedAt={fetchedAt} connected={!error} />

      <main className="content">
        {error && (
          <div className="banner banner-error" role="alert">
            <strong>Problem talking to the backend.</strong> {error}
            {roomsData && <span> Showing the last data received.</span>}
          </div>
        )}

        {loading && !roomsData ? (
          <div className="loading" role="status">
            <div className="spinner" aria-hidden="true" />
            Loading simulated sensor data…
          </div>
        ) : !roomsData ? (
          <div className="empty">
            No data to show yet. Start the backend, then use “Refresh now”.
            <div>
              <button className="btn" onClick={loadData}>Refresh now</button>
            </div>
          </div>
        ) : (
          <>
            <Controls
              threshold={threshold}
              onRefresh={loadData}
              onStep={handleStep}
              onThresholdChange={handleThresholdChange}
            />

            <SummaryCards summary={roomsData.summary} />

            <section className="grid-two">
              <BuildingMap rooms={rooms} threshold={threshold} />
              <AlertPanel rooms={rooms} threshold={threshold} />
            </section>

            <section>
              <h2 className="section-title">Room details</h2>
              <div className="room-grid">
                {rooms.map((room) => (
                  <RoomCard key={room.room_id} room={room} threshold={threshold} />
                ))}
              </div>
            </section>

            <EnergyChart series={history?.energy_series ?? []} />
          </>
        )}
      </main>

      <footer className="footer">
        Academic prototype · All readings are simulated by the backend, not measured by real sensors.
      </footer>
    </div>
  );
}
