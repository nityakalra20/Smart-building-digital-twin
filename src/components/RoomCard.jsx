import { CONDITION_LABELS, roomCondition } from "../services/helpers.js";

export default function RoomCard({ room, threshold }) {
  const condition = roomCondition(room, threshold);
  const hvacOn = room.hvac_status === "ON";

  return (
    <article className={`card room-card room-${condition}`}>
      <div className="room-card-top">
        <h3>{room.room_name}</h3>
        <span className={`hvac-badge ${hvacOn ? "hvac-on" : "hvac-off"}`}>
          HVAC {room.hvac_status}
        </span>
      </div>

      <div className="room-temp">{room.temperature_c.toFixed(1)} °C</div>
      <div className="room-condition">{CONDITION_LABELS[condition]}</div>

      <dl className="room-stats">
        <div>
          <dt>Humidity</dt>
          <dd>{room.humidity_pct.toFixed(1)} %</dd>
        </div>
        <div>
          <dt>Occupancy</dt>
          <dd>{room.occupancy} people</dd>
        </div>
        <div>
          <dt>Energy (est.)</dt>
          <dd>{room.energy_kwh.toFixed(3)} kWh</dd>
        </div>
      </dl>
    </article>
  );
}
