// api.js - every call to the Flask backend lives here.
// The backend always answers with JSON:
//   success: { success: true,  data: {...} }
//   failure: { success: false, error: { code, message } }

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5001";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkError) {
    // fetch() only throws when the server cannot be reached at all.
    throw new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Is it running? (cd backend && python app.py)`
    );
  }

  let body = null;
  try {
    body = await response.json();
  } catch (parseError) {
    throw new Error(`Backend returned an unreadable response (HTTP ${response.status}).`);
  }

  if (!response.ok || !body.success) {
    const message = body?.error?.message || `Request failed (HTTP ${response.status}).`;
    throw new Error(message);
  }
  return body.data;
}

export const getRooms = () => request("/api/rooms");

export const getHistory = (limit = 60) => request(`/api/history?limit=${limit}`);

export const runSimulationStep = () => request("/api/simulation/step", { method: "POST" });

export const getConfig = () => request("/api/config");

export const updateThreshold = (temperatureThresholdC) =>
  request("/api/config", {
    method: "PUT",
    body: JSON.stringify({ temperature_threshold_c: temperatureThresholdC }),
  });
