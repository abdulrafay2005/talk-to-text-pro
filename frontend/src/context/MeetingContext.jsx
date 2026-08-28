// MeetingContext.jsx
// Holds the shared state of the app:
//   - the list of meetings (history)
//   - the uploaded file waiting to be processed (pending upload)
//
// The list of meetings is loaded from the real backend.

import { createContext, useContext, useCallback, useState } from "react";

import { getMeetings, getErrorMessage, deleteMeeting as removeMeeting } from "../services/api.js";

const MeetingContext = createContext(null);

export function MeetingProvider({ children }) {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  // The pending upload is set by the Transcribe page and consumed
  // by the Processing page. Keeping it here means the file is never
  // lost between page navigations.
  const [pendingUpload, setPendingUpload] = useState(null);

  // Load all meetings from the backend.
  const loadMeetings = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const data = await getMeetings();
      setMeetings(data);
    } catch (error) {
      setLoadError(getErrorMessage(error, "Could not load your meetings."));
    } finally {
      setLoading(false);
    }
  }, []);

  // Add a new meeting to the top of the list.
  const addMeeting = (meeting) => {
    setMeetings((previous) => [meeting, ...previous]);
    setLoadError("");
  };

  // Replace a meeting with an updated version.
  const updateMeeting = (updated) => {
    setMeetings((previous) =>
      previous.map((meeting) => (meeting._id === updated._id ? updated : meeting))
    );
  };

  // Delete a meeting from the backend and from the list.
  const deleteMeeting = async (id) => {
    await removeMeeting(id);
    setMeetings((previous) => previous.filter((meeting) => meeting._id !== id));
  };

  const clearPendingUpload = () => setPendingUpload(null);

  return (
    <MeetingContext.Provider
      value={{
        meetings,
        loading,
        loadError,
        loadMeetings,
        addMeeting,
        updateMeeting,
        deleteMeeting,
        pendingUpload,
        setPendingUpload,
        clearPendingUpload,
      }}
    >
      {children}
    </MeetingContext.Provider>
  );
}

// Hook that pages use to reach the shared meeting state.
export function useMeetings() {
  return useContext(MeetingContext);
}