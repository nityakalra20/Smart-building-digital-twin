// helpers.js - small display helpers shared by several components.

// How far below the threshold counts as "approaching" (in °C).
const WARNING_MARGIN_C = 1.0;

// Returns "hot" (above threshold), "warm" (within 1°C below it) or "normal".
export function roomCondition(room, thresholdC) {
  if (room.temperature_c > thresholdC) return "hot";
  if (room.temperature_c > thresholdC - WARNING_MARGIN_C) return "warm";
  return "normal";
}

export const CONDITION_LABELS = {
  hot: "Above threshold",
  warm: "Near threshold",
  normal: "Comfortable",
};

// Timestamps from the backend look like "2026-10-28T16:27:16".
// Cutting the text avoids time-zone confusion in the browser.
export function timeOnly(timestamp) {
  return timestamp ? timestamp.slice(11, 19) : "--";
}

export function dateAndTime(timestamp) {
  return timestamp ? timestamp.replace("T", " ") : "--";
}
