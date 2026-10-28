import { roomCondition } from "../services/helpers.js";

// A simple floor-plan style picture. Each block's colour shows the room's condition:
//   green = comfortable, amber = within 1°C of the threshold, red = above the threshold.
export default function BuildingMap({ rooms, threshold }) {
  const byId = Object.fromEntries(rooms.map((r) => [r.room_id, r]));

  function Block({ roomId, className }) {
    const room = byId[roomId];
    if (!room) return <div className={`map-room map-missing ${className}`}>No data</div>;
    const condition = roomCondition(room, threshold);
    return (
      <div className={`map-room map-${condition} ${className}`}>
        <div className="map-name">{room.room_name}</div>
        <div className="map-temp">{room.temperature_c.toFixed(1)} °C</div>
        <div className="map-meta">
          {room.occupancy} people · HVAC {room.hvac_status}
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="section-title">Building floor view</h2>
      <div className="map" role="img" aria-label="Simplified floor plan of the three rooms">
        <Block roomId="room-101" className="map-a" />
        <Block roomId="room-102" className="map-b" />
        <Block roomId="conference-room" className="map-c" />
      </div>
      <ul className="legend">
        <li><span className="swatch swatch-normal" /> Comfortable</li>
        <li><span className="swatch swatch-warm" /> Within 1 °C of threshold</li>
        <li><span className="swatch swatch-hot" /> Above threshold</li>
      </ul>
    </div>
  );
}
