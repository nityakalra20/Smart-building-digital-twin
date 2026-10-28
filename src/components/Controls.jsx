import { useEffect, useState } from "react";

// Buttons for the demonstration: refresh, run one simulation step, change the threshold.
export default function Controls({ threshold, onRefresh, onStep, onThresholdChange }) {
  const [inputValue, setInputValue] = useState(String(threshold));
  const [message, setMessage] = useState(null); // {type: "ok" | "error", text}
  const [busy, setBusy] = useState(false);

  // Keep the box in sync when the backend value changes.
  useEffect(() => {
    setInputValue(String(threshold));
  }, [threshold]);

  async function applyThreshold(event) {
    event.preventDefault();
    const number = Number(inputValue);
    if (inputValue.trim() === "" || Number.isNaN(number)) {
      setMessage({ type: "error", text: "Please enter a number, for example 24." });
      return;
    }
    setBusy(true);
    try {
      await onThresholdChange(number);
      setMessage({ type: "ok", text: `Threshold set to ${number} °C.` });
    } catch (err) {
      // e.g. "temperature_threshold_c must be between 15.0 and 40.0."
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card controls">
      <form className="threshold-form" onSubmit={applyThreshold}>
        <label htmlFor="threshold">HVAC threshold (°C)</label>
        <input
          id="threshold"
          type="number"
          step="0.5"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <button className="btn btn-primary" type="submit" disabled={busy}>
          Apply
        </button>
      </form>

      <div className="control-buttons">
        <button className="btn" onClick={onRefresh}>Refresh now</button>
        <button className="btn" onClick={onStep}>Run one simulation step</button>
      </div>

      <p className="rule-note">
        Rule: HVAC is ON when a room is above {threshold.toFixed(1)} °C, OFF at or below it.
        (Software rule only — no real HVAC is controlled.)
      </p>
      {message && <p className={`form-message form-${message.type}`}>{message.text}</p>}
    </section>
  );
}
