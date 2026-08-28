// MeetingCard.jsx
// One meeting shown in the dashboard grid and on the history page.

import { Link } from "react-router-dom";
import {
  FileText,
  Calendar,
  Clock,
  Trash2,
  ArrowRight,
  Smile,
  Frown,
  Meh,
} from "lucide-react";

import { formatDate, formatDuration } from "../utils/format.js";

function SentimentIcon({ sentiment }) {
  const value = (sentiment || "neutral").toLowerCase();
  if (value === "positive") return <Smile size={12} />;
  if (value === "negative") return <Frown size={12} />;
  return <Meh size={12} />;
}

function MeetingCard({ meeting, onDelete }) {
  return (
    <Link to={`/meetings/${meeting._id}`} className="meeting-card">
      <div className="mc-top">
        <span className="mc-icon">
          <FileText size={17} />
        </span>
      </div>

      <h3 className="mc-title">{meeting.title}</h3>

      <div className="mc-meta">
        <span>
          <Calendar size={13} />
          {formatDate(meeting.created_at)}
        </span>
        <span className="sep" aria-hidden="true">·</span>
        <span>
          <Clock size={13} />
          {formatDuration(meeting.duration)}
        </span>
        <span className="sep" aria-hidden="true">·</span>
        <span className={`mc-sent mc-sent-${(meeting.sentiment || "neutral").toLowerCase()}`}>
          <SentimentIcon sentiment={meeting.sentiment} />
          {meeting.sentiment || "Neutral"}
        </span>
        <span className="tag tag-type">{meeting.meeting_type}</span>
      </div>

      <p className="mc-summary">{meeting.summary}</p>

      <div className="mc-footer">
        <span className="mc-view">
          View summary
          <ArrowRight size={14} />
        </span>

        {onDelete && (
          <button
            className="mc-delete"
            title="Delete meeting"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onDelete(meeting);
            }}
          >
            <Trash2 size={14} />
            Delete
          </button>
        )}
      </div>
    </Link>
  );
}

export default MeetingCard;