// Alerts are created from the rooms data: any room hotter than the threshold gets one.
export default function AlertPanel({ rooms, threshold }) {
  const alerts = rooms.filter((room) => room.temperature_c > threshold);

  return (
    <div className="card">
      <h2 className="section-title">
        Alerts <span className="count">{alerts.length}</span>
      </h2>

      {alerts.length === 0 ? (
        <p className="all-clear">✔ All rooms are at or below {threshold.toFixed(1)} °C.</p>
      ) : (
        <ul className="alert-list">
          {alerts.map((room) => {
            const over = room.temperature_c - threshold;
            return (
              <li key={room.room_id} className="alert-item">
                <strong>{room.room_name}</strong> is {room.temperature_c.toFixed(1)} °C —{" "}
                {over.toFixed(1)} °C above the {threshold.toFixed(1)} °C threshold.
                <div className="alert-sub">HVAC status: {room.hvac_status}</div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
