import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { timeOnly } from "../services/helpers.js";

const ROOM_LINES = [
  { key: "room-101", name: "Room 101", color: "#2563eb" },
  { key: "room-102", name: "Room 102", color: "#059669" },
  { key: "conference-room", name: "Conference Room", color: "#d97706" },
];

export default function EnergyChart({ series }) {
  // Turn each history point into a flat object that Recharts understands.
  const data = series.map((point) => ({
    time: timeOnly(point.timestamp),
    total: point.total_energy_kwh,
    ...point.by_room,
  }));

  return (
    <div className="card">
      <h2 className="section-title">Historical energy consumption (estimated)</h2>
      <p className="muted">
        Read from the saved CSV file. Each point is the estimated energy of one simulation step.
      </p>

      {data.length === 0 ? (
        <div className="empty">No history saved yet.</div>
      ) : (
        <div className="chart-box">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} minTickGap={30} />
              <YAxis tick={{ fontSize: 12 }} label={{ value: "kWh", angle: -90, position: "insideLeft" }} />
              <Tooltip formatter={(value) => `${Number(value).toFixed(3)} kWh`} />
              <Legend />
              <Line type="monotone" dataKey="total" name="Total" stroke="#111827" strokeWidth={3} dot={false} isAnimationActive={false} />
              {ROOM_LINES.map((line) => (
                <Line
                  key={line.key}
                  type="monotone"
                  dataKey={line.key}
                  name={line.name}
                  stroke={line.color}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
