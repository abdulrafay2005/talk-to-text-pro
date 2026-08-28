import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Mic,
  FileText,
  Clock3,
  ArrowRight,
  ArrowUpRight,
} from "lucide-react";

import MeetingCard from "../components/MeetingCard.jsx";
import Alert from "../components/Alert.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useMeetings } from "../context/MeetingContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  formatNumber,
  getGreeting,
} from "../utils/format.js";

function Metric({ icon: Icon, label, value, accent = false }) {
  return (
    <div className={`dashboard-metric${accent ? " metric-accent" : ""}`}>
      <span className="metric-icon">
        <Icon size={16} strokeWidth={1.9} />
      </span>
      <span>
        <span className="metric-label">{label}</span>
        <strong className="metric-value">{value}</strong>
      </span>
    </div>
  );
}

function DashboardPage() {
  const navigate = useNavigate();

  const { user } = useAuth();

  const {
    meetings,
    loading,
    loadError,
    loadMeetings,
    deleteMeeting,
  } = useMeetings();

  useEffect(() => {
    loadMeetings();
  }, [loadMeetings]);

  const firstName = user?.name?.split(" ")[0] || "there";

  const totalSeconds = meetings.reduce(
    (sum, meeting) => sum + (Number(meeting.duration) || 0),
    0
  );

  const totalMinutes = Math.round(totalSeconds / 60);

  const latestMeeting = meetings[0];

  const handleDelete = async (meeting) => {
    if (!window.confirm("Delete this meeting?")) return;

    try {
      await deleteMeeting(meeting._id);
    } catch {
      window.alert("Could not delete this meeting. Please try again.");
    }
  };

  return (
    <div className="page dashboard-page page-fade">

      {/* Header */}
      <header className="dashboard-header">
        <div>
          <div className="dashboard-eyebrow">
            <span className="status-dot" />
            Your workspace
          </div>

          <h1 className="dashboard-title">
            {getGreeting()}, {firstName}.
          </h1>

          <p className="dashboard-subtitle">
            Your meetings, transcripts, and insights — all in one place.
          </p>
        </div>

        <button
          className="btn btn-primary dashboard-cta"
          onClick={() => navigate("/transcribe")}
        >
          <Plus size={16} strokeWidth={2.2} />
          New meeting
        </button>
      </header>

      {loadError && (
        <Alert
          type="error"
          message={loadError}
          onRetry={loadMeetings}
        />
      )}

      {/* Overview metrics */}
      {!loading && (
        <section className="dashboard-metrics" aria-label="Workspace overview">

          <Metric
            icon={FileText}
            label="Meetings"
            value={formatNumber(meetings.length)}
          />

          <Metric
            icon={Clock3}
            label="Time analyzed"
            value={`${totalMinutes}m`}
          />

        </section>
      )}

      {/* Latest analysis */}
      {!loading && !!latestMeeting && (
        <section className="latest-analysis">

          <div className="latest-analysis-main">
            <span className="overview-kicker">
              Latest analysis
            </span>

            <h2>Your meeting intelligence is ready</h2>

            <p>
              "{latestMeeting.title}" has been fully processed. Review the
              summary, decisions, action items and transcript.
            </p>

            <button
              className="overview-link"
              onClick={() =>
                navigate(`/meetings/${latestMeeting._id}`)
              }
            >
              Open latest meeting
              <ArrowRight size={15} />
            </button>
          </div>

        </section>
      )}

      {/* Recent meetings */}
      <section className="recent-section">

        <div className="recent-header">
          <h2 className="recent-title">Recent meetings</h2>

          {meetings.length > 0 && (
            <button
              className="text-button"
              onClick={() => navigate("/meetings")}
            >
              View all
              <ArrowUpRight size={14} />
            </button>
          )}
        </div>

        {loading ? (
          <div className="meetings-grid">
            {[1, 2, 3].map((n) => (
              <SkeletonCard key={n} />
            ))}
          </div>
        ) : meetings.length === 0 ? (
          <div className="dashboard-empty">

            <div className="empty-icon">
              <Mic size={22} />
            </div>

            <h3>No meetings yet</h3>

            <p>
              Upload your first recording and we'll turn it into a
              searchable meeting workspace.
            </p>

            <button
              className="btn btn-primary"
              onClick={() => navigate("/transcribe")}
            >
              <Plus size={15} />
              Analyze your first meeting
            </button>

          </div>
        ) : (
          <div className="meetings-grid">
            {meetings.slice(0, 3).map((meeting) => (
              <MeetingCard
                key={meeting._id}
                meeting={meeting}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}

      </section>

    </div>
  );
}

export default DashboardPage;