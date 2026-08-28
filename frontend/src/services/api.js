// api.js
// All the requests the frontend sends to the Flask backend.
// The Vite dev server forwards /api requests to http://localhost:5000.
//
// These endpoints match the EXISTING backend exactly:
//   POST   /api/auth/register
//   POST   /api/auth/login
//   GET    /api/auth/me
//   POST   /api/auth/logout
//   POST   /api/transcribe
//   GET    /api/meetings
//   GET    /api/meetings/<id>
//   DELETE /api/meetings/<id>
//   POST   /api/meetings/<id>/translate
//   POST   /api/meetings/<id>/ask
//   GET    /api/meetings/<id>/pdf

import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  timeout: 0,
});

// ---------- Authentication ----------

// Create a new account.
export function register({ name, email, password }) {
  return api.post("/auth/register", { name, email, password }).then((res) => res.data);
}

// Sign in. The backend starts a session cookie on success.
export function login({ email, password }) {
  return api.post("/auth/login", { email, password }).then((res) => res.data);
}

// End the session.
export function logout() {
  return api.post("/auth/logout").then((res) => res.data);
}

// Return the logged-in user (used to restore the session on app start).
export function getCurrentUser() {
  return api.get("/auth/me").then((res) => res.data.user);
}

// ---------- Meetings ----------

// Upload a file and run the full pipeline (transcribe + clean +
export function uploadMeeting(formData) {
  console.log("🚀 uploadMeeting CALLED");

  for (const [key, value] of formData.entries()) {
    console.log(
      "FORM DATA:",
      key,
      value instanceof File
        ? `${value.name} (${value.size} bytes)`
        : value
    );
  }

  console.log("📤 Sending POST /transcribe...");

  return api
    .post("/transcribe", formData)
    .then((res) => {
      console.log("✅ TRANSCRIBE RESPONSE:", res.data);
      return res.data;
    })
    .catch((err) => {
      console.error("❌ TRANSCRIBE ERROR:", err);
      console.error("CODE:", err.code);
      console.error("MESSAGE:", err.message);
      console.error("RESPONSE:", err.response);
      throw err;
    });
}


// Get the list of saved meetings (history) for the logged-in user.
export function getMeetings() {
  return api.get("/meetings").then((res) => res.data.meetings);
}

// Get a single meeting by id.
export function getMeeting(id) {
  return api.get(`/meetings/${id}`).then((res) => res.data.meeting);
}

// Delete a meeting by id.
export function deleteMeeting(id) {
  return api.delete(`/meetings/${id}`).then((res) => res.data);
}

// Translate an already saved meeting into a target language.
export function requestTranslation(id, target) {
  return api
    .post(`/meetings/${id}/translate`, { target })
    .then((res) => res.data.meeting);
}

// Ask a real question about a meeting (answered by the AI using
// only the meeting transcript). Returns the answer text.
export function askMeeting(id, question) {
  return api
    .post(`/meetings/${id}/ask`, { question })
    .then((res) => res.data.answer);
}

// Full URL for downloading the PDF report of a meeting.
export function downloadPDF(id) {
  return `/api/meetings/${id}/pdf`;
}

// Full URL for downloading the Word (.docx) report of a meeting.
export function downloadDOCX(id) {
  return `/api/meetings/${id}/docx`;
}

// Enable sharing for a meeting. Returns { share_token, share_url }.
export function shareMeeting(id) {
  return api.post(`/meetings/${id}/share`).then((res) => res.data);
}

// Disable sharing for a meeting.
export function unshareMeeting(id) {
  return api.delete(`/meetings/${id}/share`).then((res) => res.data);
}

// Fetch a meeting through its public share link (read-only, no login).
export function getSharedMeeting(token) {
  return api.get(`/shared/${token}`).then((res) => res.data.meeting);
}

// Turn any axios error into a friendly, human-readable message.
// We never show raw Flask errors to the user.
export function getErrorMessage(error, fallback) {
  const backendMessage = error?.response?.data?.error;
  if (backendMessage) return backendMessage;
  if (error?.code === "ECONNABORTED") return "The request took too long. Please try again.";
  if (error?.response?.status === 401) return "Your session has expired. Please sign in again.";
  if (error?.response?.status === 404) return "This meeting could not be found.";
  if (error?.response?.status === 500) return "Something went wrong on the server. Please try again.";
  if (error?.request) return "Unable to connect to TalkToText Pro. Make sure the backend is running.";
  return fallback || "Something went wrong. Please try again.";
}