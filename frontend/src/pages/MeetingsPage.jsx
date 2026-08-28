// MeetingsPage.jsx
// Full meeting history with search. All data comes from the REAL backend
// through the meetings context (MongoDB via Flask).

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, FolderOpen, Plus } from "lucide-react";

import MeetingCard from "../components/MeetingCard.jsx";
import Alert from "../components/Alert.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useMeetings } from "../context/MeetingContext.jsx";

function MeetingsPage() {
  const navigate = useNavigate();
  const { meetings, loading, loadError, loadMeetings, deleteMeeting } = useMeetings();
  const [query, setQuery] = useState("");

  // Reload the history from the backend whenever this page is opened.
  useEffect(() => {
    loadMeetings();
  }, [loadMeetings]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return meetings;
    return meetings.filter((meeting) =>
      [meeting.title, meeting.meeting_type, meeting.summary]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(term))
    );
  }, [meetings, query]);

  const handleDelete = async (meeting) => {
    if (!window.confirm(`Delete "${meeting.title}"?`)) return;
    try {
      await deleteMeeting(meeting._id);
    } catch {
      window.alert("Could not delete this meeting. Please try again.");
    }
  };

  return (
    <div className="page page-fade">
      <div className="history-toolbar">
        <div>
          <h1 className="dash-title">Meeting History</h1>
          <p className="dash-sub">
            {meetings.length} meeting{meetings.length === 1 ? "" : "s"} saved
          </p>
        </div>

        <div className="search-wrap">
          <Search size={16} className="search-icon" />
          <input
            className="search-input"
            type="text"
            placeholder="Search meetings..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      </div>

      {loadError && <Alert type="error" message={loadError} onRetry={loadMeetings} />}

      {loading ? (
        <div className="meetings-grid">
          {[1, 2, 3, 4].map((n) => (
            <SkeletonCard key={n} />
          ))}
        </div>
      ) : meetings.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <FolderOpen size={28} />
          </div>
          <h3>No meetings yet</h3>
          <p>Transcribe your first recording and it will show up here.</p>
          <button className="btn btn-primary" onClick={() => navigate("/transcribe")}>
            <Plus size={16} />
            Analyze a meeting
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Search size={28} />
          </div>
          <h3>No matches for "{query}"</h3>
          <p>Try a different search term.</p>
        </div>
      ) : (
        <div className="meetings-grid">
          {filtered.map((meeting) => (
            <MeetingCard key={meeting._id} meeting={meeting} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

export default MeetingsPage;