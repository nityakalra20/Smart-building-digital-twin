import { dateAndTime } from "../services/helpers.js";

export default function Header({ lastUpdated, fetchedAt, connected }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div>
          <h1>Smart Building Digital Twin</h1>
          <p className="subtitle">Live software model of three rooms</p>
        </div>
        <div className="header-right">
          <span className="sim-badge">Simulated Sensor Data</span>
          <span className={`connection ${connected ? "connection-ok" : "connection-bad"}`}>
            <span className="dot" /> {connected ? "Backend connected" : "Backend unavailable"}
          </span>
          <span className="last-updated">
            Last updated: <strong>{dateAndTime(lastUpdated)}</strong>
            {fetchedAt && <> · fetched {fetchedAt.toLocaleTimeString()}</>}
          </span>
        </div>
      </div>
    </header>
  );
}
