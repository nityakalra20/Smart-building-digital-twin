function Card({ label, value, unit, note }) {
  return (
    <div className="card summary-card">
      <div className="summary-label">{label}</div>
      <div className="summary-value">
        {value}
        <span className="summary-unit">{unit}</span>
      </div>
      {note && <div className="summary-note">{note}</div>}
    </div>
  );
}

export default function SummaryCards({ summary }) {
  const show = (v, digits = 1) => (v === null || v === undefined ? "--" : Number(v).toFixed(digits));

  return (
    <section className="summary-grid" aria-label="Building summary">
      <Card label="Average temperature" value={show(summary.average_temperature_c)} unit=" °C" />
      <Card label="Average humidity" value={show(summary.average_humidity_pct)} unit=" %" />
      <Card label="Total occupancy" value={summary.total_occupancy} unit=" people" />
      <Card
        label="Estimated energy usage"
        value={show(summary.total_energy_kwh, 2)}
        unit=" kWh"
        note="latest step, all rooms (estimate)"
      />
    </section>
  );
}
