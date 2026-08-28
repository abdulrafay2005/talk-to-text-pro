// TranscriptView.jsx
// Reusable content sections used on the meeting detail page:
//   - SectionList   : a bullet list of items (key points, decisions, ...)
//   - TopicsList    : topics rendered as small tags
//   - TranscriptCard: the readable transcript. Shows timestamped rows when
//                     the backend provides "segments", otherwise a clean
//                     text block. Supports Original / Translated tabs.

import { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, GitBranch, MessageSquareText } from "lucide-react";

import { formatTimestamp } from "../utils/format.js";

// A bullet list of items with an optional leading icon.
export function SectionList({ title, items, icon: Icon = CheckCircle2, emptyText }) {
  const list = items && Array.isArray(items) ? items : [];

  return (
    <section className="card section-card">
      <div className="section-head">
        <Icon size={17} />
        <h3>{title}</h3>
      </div>
      {list.length === 0 ? (
        <p className="muted">{emptyText || "Nothing was explicitly stated."}</p>
      ) : (
        <ul className="keypoint-list">
          {list.map((item, index) => (
            <li key={index} className="keypoint">
              <Icon size={15} className="kp-icon" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Topics displayed as small tags.
export function TopicsList({ title, items, icon: Icon = GitBranch }) {
  const list = items && Array.isArray(items) ? items : [];

  return (
    <section className="card section-card">
      <div className="section-head">
        <Icon size={17} />
        <h3>{title}</h3>
      </div>
      <div className="topic-tags">
        {list.length === 0 ? (
          <span className="muted">Nothing was explicitly stated.</span>
        ) : (
          list.map((topic, index) => (
            <span key={index} className="tag tag-type">
              {topic}
            </span>
          ))
        )}
      </div>
    </section>
  );
}

// The main transcript card with Original / Translated toggle.
export function TranscriptCard({
  segments,
  originalText,
  translatedText,
  translatedLabel,
}) {
  const hasTranslation = Boolean(translatedText);
  const [tab, setTab] = useState("original");
  const [collapsed, setCollapsed] = useState(false);

  const showSegments = tab === "original" && segments && segments.length > 0;
  const bodyText =
    tab === "translated" ? translatedText : originalText;

  return (
    <section className="card section-card transcript-card">
      <div className="section-head">
        <MessageSquareText size={17} />
        <h3>Transcript</h3>
      </div>

      {hasTranslation && (
        <div className="opt-tabs">
          <button
            className={`opt-tab ${tab === "original" ? "active" : ""}`}
            onClick={() => setTab("original")}
          >
            Original
          </button>
          <button
            className={`opt-tab ${tab === "translated" ? "active" : ""}`}
            onClick={() => setTab("translated")}
          >
            Translated
          </button>
        </div>
      )}

      {hasTranslation && translatedLabel && (
        <p className="hint" style={{ marginBottom: 16 }}>
          Translation: {translatedLabel}
        </p>
      )}

      {!collapsed &&
        (showSegments ? (
          <div>
            {segments.map((segment, index) => (
              <div key={index} className="seg-row">
                <span className="seg-time">{formatTimestamp(segment.start)}</span>
                <span className="seg-text">{segment.text}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="transcript-body">
            {bodyText || "No transcript available for this meeting."}
          </p>
        ))}

      {bodyText && bodyText.length > 900 && (
        <button
          className="collapse-btn"
          onClick={() => setCollapsed((value) => !value)}
        >
          {collapsed ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
          {collapsed ? "Show full transcript" : "Show less"}
        </button>
      )}
    </section>
  );
}