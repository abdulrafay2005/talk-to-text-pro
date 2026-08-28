// SharePage.jsx
// Read-only view reached through a meeting's public share link
// (/share/:token). Anyone with the link can read the meeting, but it
// has no edit, ask, translate or delete actions.

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Calendar,
  Clock,
  CheckCircle2,
  GitBranch,
  Scale,
  Users,
  AlertTriangle,
  MessageSquareText,
  Lock,
} from "lucide-react";

import Alert from "../components/Alert.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { SectionList, TopicsList, TranscriptCard } from "../components/TranscriptView.jsx";
import { getSharedMeeting, getErrorMessage } from "../services/api.js";
import { formatDate, formatDuration, languageName } from "../utils/format.js";

function SentimentBadge({ sentiment }) {
  const value = (sentiment || "neutral").toLowerCase();
  return (
    <span className={`sentiment sentiment-${value}`}>
      <span className={`sentiment-dot sentiment-dot-${value}`} />
      {sentiment || "Neutral"}
    </span>
  );
}

function SharePage() {
  const { token } = useParams();

  const [meeting, setMeeting] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getSharedMeeting(token)
      .then(setMeeting)
      .catch((err) =>
        setError(getErrorMessage(err, "This shared meeting could not be loaded."))
      )
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="page page-fade">
        <div className="meetings-grid" style={{ gridTemplateColumns: "1fr" }}>
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (!meeting && error) {
    return (
      <div className="page page-fade" style={{ textAlign: "center" }}>
        <Alert type="error" message={error} />
        <p className="hint" style={{ marginTop: 16 }}>
          Ask the meeting owner for a valid link.
        </p>
      </div>
    );
  }

  const actionItems = meeting.action_items || [];
  const unresolved = meeting.unresolved_issues || [];
  const segments = meeting.segments || [];

  return (
    <div className="page page-fade">
      <p className="hint" style={{ marginBottom: 8 }}>
        <Lock size={13} style={{ verticalAlign: "-2px", marginRight: 6 }} />
        Read-only shared meeting
      </p>

      {/* Header */}
      <header className="card detail-hero" style={{ marginBottom: 22 }}>
        <div className="hero-main">
          <div className="hero-tag-row">
            <span className="tag tag-type">{meeting.meeting_type || "General Meeting"}</span>
            <SentimentBadge sentiment={meeting.sentiment} />
          </div>
          <h1>{meeting.title}</h1>
          <div className="meta-row">
            <span>
              <Calendar size={14} />
              {formatDate(meeting.created_at)}
            </span>
            <span>
              <Clock size={14} />
              {formatDuration(meeting.duration)}
            </span>
            <span>
              <MessageSquareText size={14} />
              {languageName(meeting.original_language)}
            </span>
          </div>
        </div>
      </header>

      {/* Summary */}
      <section className="card summary-card">
        <div className="section-head">
          <MessageSquareText size={17} />
          <h3>AI Summary</h3>
        </div>
        <p className="summary-text">{meeting.summary}</p>
      </section>

      {/* Key Points / Topics / Decisions */}
      <div>
        <SectionList title="Key Points" items={meeting.key_points} icon={CheckCircle2} />
      </div>
      <div>
        <TopicsList title="Topics" items={meeting.topics} icon={GitBranch} />
      </div>
      <div>
        <SectionList title="Decisions" items={meeting.decisions} icon={Scale} />
      </div>

      {/* Action Items */}
      <section className="card section-card">
        <div className="section-head">
          <Users size={17} />
          <h3>Action Items</h3>
        </div>
        {actionItems.length === 0 ? (
          <p className="muted">No action items were explicitly stated.</p>
        ) : (
          <div className="action-table-wrap">
            <table className="action-table">
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Task</th>
                  <th>Deadline</th>
                </tr>
              </thead>
              <tbody>
                {actionItems.map((item, index) => (
                  <tr key={index}>
                    <td>
                      <strong>{item.person}</strong>
                    </td>
                    <td>{item.task}</td>
                    <td>{item.deadline}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Unresolved Issues */}
      {unresolved.length > 0 && (
        <div>
          <SectionList
            title="Unresolved Issues"
            items={unresolved}
            icon={AlertTriangle}
            emptyText="No unresolved issues."
          />
        </div>
      )}

      {/* Transcript */}
      <div>
        <TranscriptCard
          segments={segments}
          originalText={meeting.transcript_cleaned || meeting.transcript_raw}
          translatedText={meeting.translated_transcript}
          translatedLabel={meeting.translate_to ? languageName(meeting.translate_to) : ""}
        />
      </div>
    </div>
  );
}

export default SharePage;