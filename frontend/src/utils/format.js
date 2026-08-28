// format.js
// Small helper functions used across the frontend for
// durations, dates, language names, and so on.

const LANGUAGE_NAMES = {
  en: "English",
  es: "Spanish",
  fr: "French",
  de: "German",
  it: "Italian",
  pt: "Portuguese",
  nl: "Dutch",
  tr: "Turkish",
  ur: "Urdu",
  ar: "Arabic",
  hi: "Hindi",
  bn: "Bengali",
  zh: "Chinese",
  ja: "Japanese",
  ko: "Korean",
  ru: "Russian",
};

// Turn seconds into something like "4m 32s" or "1h 5m".
export function formatDuration(seconds) {
  if (seconds === undefined || seconds === null) return "—";
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

// Turn seconds into a 00:00 style timestamp.
export function formatTimestamp(seconds) {
  const s = Math.floor(seconds || 0);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

// Display the backend language code (like "en") as a friendly name.
export function languageName(code) {
  if (!code) return "Unknown";
  return LANGUAGE_NAMES[code.toLowerCase()] || code;
}

// Format the "2026-08-27 10:00:00" string returned by the backend.
export function formatDate(dateString) {
  if (!dateString) return "";
  // Safari needs slashes instead of dashes for this format.
  const date = new Date(dateString.replace(/-/g, "/"));
  if (isNaN(date)) return dateString;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Time-of-day greeting used on the dashboard.
export function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

// Turn bytes into a readable file size.
export function formatFileSize(bytes) {
  if (!bytes || bytes < 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// Format a number with thousands separators: 1250 -> "1,250".
export function formatNumber(value) {
  const number = Number(value);
  if (!isFinite(number)) return "0";
  return number.toLocaleString();
}

// Format a large number compactly: 2400 -> "2.4K", 1500000 -> "1.5M".
export function formatCompact(value) {
  const number = Number(value);
  if (!isFinite(number)) return "0";
  if (number >= 1000000) return `${(number / 1000000).toFixed(1)}M`;
  if (number >= 1000) return `${(number / 1000).toFixed(1)}K`;
  return String(Math.round(number));
}