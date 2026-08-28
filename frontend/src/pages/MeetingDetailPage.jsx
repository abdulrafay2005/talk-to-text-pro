// MeetingDetailPage.jsx
// The strongest screen - full meeting intelligence for one meeting.
// Every value shown here comes from the real backend.

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Download,
  FileText,
  Share2,
  Trash2,
  Sparkles,
  CheckCircle2,
  GitBranch,
  Scale,
  Users,
  AlertTriangle,
  MessageSquareText,
  Languages,
  Loader2,
  Send,
  Info,
  Gauge,
} from "lucide-react";

import Alert from "../components/Alert.jsx";
import { SectionList, TopicsList, TranscriptCard } from "../components/TranscriptView.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import {
  getMeeting,
  downloadPDF,
  downloadDOCX,
  shareMeeting,
  requestTranslation,
  askMeeting,
  getErrorMessage,
} from "../services/api.js";
import { useMeetings } from "../context/MeetingContext.jsx";
import { formatDate, formatDuration, languageName } from "../utils/format.js";

const TRANSLATE_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ur", label: "Urdu" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "ar", label: "Arabic" },
  { code: "hi", label: "Hindi" },
  { code: "de", label: "German" },
];

function SentimentBadge({ sentiment }) {
  const value = (sentiment || "neutral").toLowerCase();
  return (
    <span className={`sentiment sentiment-${value}`}>
      <span className={`sentiment-dot sentiment-dot-${value}`} />
      {sentiment || "Neutral"}
    </span>
  );
}

function MeetingDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { deleteMeeting } = useMeetings();

  const [meeting, setMeeting] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [translateTo, setTranslateTo] = useState("es");
  const [translating, setTranslating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Share state.
  const [sharing, setSharing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shareLink, setShareLink] = useState("");

  // Ask-your-meeting state (answered by the real AI through the backend).
  const [question, setQuestion] = useState("");
  const [askAnswer, setAskAnswer] = useState(null);
  const [asking, setAsking] = useState(false);

  const loadMeeting = () => {
    setLoading(true);
    setError("");
    getMeeting(id)
      .then((data) => setMeeting(data))
      .catch((err) => setError(getErrorMessage(err, "Something went wrong while loading this meeting.")))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadMeeting();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm("Delete this meeting?")) return;
    setDeleting(true);
    setError("");
    try {
      await deleteMeeting(id);
      navigate("/meetings", { replace: true });
    } catch {
      setError("Could not delete this meeting. Please try again.");
      setDeleting(false);
    }
  };

  const handleShare = async () => {
    if (sharing) return;
    setSharing(true);
    setError("");
    try {
      const { share_token: token } = await shareMeeting(id);
      const link = `${window.location.origin}/share/${token}`;
      setShareLink(link);
      try {
        await navigator.clipboard.writeText(link);
        setCopied(true);
      } catch {
        setCopied(false);
      }
      window.setTimeout(() => setCopied(false), 3000);
    } catch (err) {
      setError(getErrorMessage(err, "Could not share this meeting. Please try again."));
    } finally {
      setSharing(false);
    }
  };

  const handleTranslate = async () => {
    setTranslating(true);
    setError("");
    try {
      const updated = await requestTranslation(id, translateTo);
      setMeeting(updated);
    } catch (err) {
      setError(getErrorMessage(err, "Translation failed. Please try again."));
    } finally {
      setTranslating(false);
    }
  };

  const handleAsk = async () => {
    if (!question.trim() || asking) return;
    const asked = question.trim();
    setQuestion("");
    setAsking(true);
    setAskAnswer(null);
    setError("");
    try {
      const answer = await askMeeting(id, asked);
      setAskAnswer(answer);
    } catch (err) {
      setError(getErrorMessage(err, "Could not get an answer. Please try again."));
    } finally {
      setAsking(false);
    }
  };

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
      <div className="page page-fade">
        <Alert type="error" message={error} onRetry={loadMeeting} />
        <button className="btn btn-secondary" onClick={() => navigate("/meetings")}>
          <ArrowLeft size={15} />
          Back to meetings
        </button>
      </div>
    );
  }

  const pdfUrl = downloadPDF(id);
  const actionItems = meeting.action_items || [];
  const unresolved = meeting.unresolved_issues || [];
  const segments = meeting.segments || [];

  return (
    <div className="page page-fade">
      <button className="back-link" onClick={() => navigate(-1)}>
        <ArrowLeft size={16} />
        Back
      </button>

      {error && <Alert type="error" message={error} />}

      {/* ---------- Header ---------- */}
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
              <Languages size={14} />
              {languageName(meeting.original_language)}
            </span>
          </div>
        </div>

        <div className="hero-actions">
          <a className="btn btn-primary" href={pdfUrl}>
            <Download size={16} />
            Export PDF
          </a>
          <a className="btn btn-secondary" href={downloadDOCX(id)}>
            <FileText size={16} />
            Export Word
          </a>
          <button className="btn btn-secondary" onClick={handleShare} disabled={sharing}>
            {sharing ? <Loader2 size={16} className="spin" /> : <Share2 size={16} />}
            {sharing ? "Creating..." : copied ? "Copied!" : "Share"}
          </button>
          <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
            Delete
          </button>
        </div>
      </header>

      {shareLink && (
        <section className="card share-card" style={{ marginBottom: 22 }}>
          <div className="section-head">
            <Share2 size={17} />
            <h3>Share link</h3>
          </div>
          <p className="hint" style={{ margin: 0 }}>
            Anyone with this link can read this meeting (read-only). Your transcript
            and notes are only shared when you use this button.
          </p>
          <div className="share-link-row">
            <code className="share-link">{shareLink}</code>
            <button
              className="btn btn-secondary"
              onClick={() => {
                navigator.clipboard.writeText(shareLink);
                setCopied(true);
                window.setTimeout(() => setCopied(false), 3000);
              }}
            >
              {copied ? "Copied!" : "Copy link"}
            </button>
          </div>
        </section>
      )}

      {/* ---------- AI Summary ---------- */}
      <section className="card summary-card">
        <div className="section-head">
          <Sparkles size={17} />
          <h3>AI Summary</h3>
        </div>
        <p className="summary-text">{meeting.summary}</p>
      </section>

      {/* ---------- AI Analysis Context ---------- */}
      <section className="card section-card">
        <div className="section-head">
          <Gauge size={17} />
          <h3>AI Analysis Context</h3>
        </div>
        <p className="muted" style={{ margin: 0 }}>
          The meeting transcript is analyzed by the AI within its context limit
          (a long transcript is split into chunks so nothing is skipped).
          Your transcript below is always shown unmodified.
        </p>
      </section>

      {/* ---------- Key Points ---------- */}
      <div>
        <SectionList title="Key Points" items={meeting.key_points} icon={CheckCircle2} />
      </div>

      {/* ---------- Topics ---------- */}
      <div>
        <TopicsList title="Topics" items={meeting.topics} icon={GitBranch} />
      </div>

      {/* ---------- Decisions ---------- */}
      <div>
        <SectionList title="Decisions" items={meeting.decisions} icon={Scale} />
      </div>

      {/* ---------- Action Items ---------- */}
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

      {/* ---------- Unresolved Issues (only when present) ---------- */}
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

      {/* ---------- Transcript ---------- */}
      <div>
        <TranscriptCard
          segments={segments}
          originalText={meeting.transcript_cleaned || meeting.transcript_raw}
          translatedText={meeting.translated_transcript}
          translatedLabel={meeting.translate_to ? languageName(meeting.translate_to) : ""}
        />
      </div>

      {/* ---------- Optional translation ---------- */}
      <section className="card section-card">
        <div className="section-head">
          <Languages size={17} />
          <h3>Translation</h3>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <select
            className="select"
            style={{ maxWidth: 220 }}
            value={translateTo}
            onChange={(event) => setTranslateTo(event.target.value)}
          >
            {TRANSLATE_LANGUAGES.map((language) => (
              <option key={language.code} value={language.code}>
                {language.label}
              </option>
            ))}
          </select>
          <button className="btn btn-secondary" onClick={handleTranslate} disabled={translating}>
            {translating ? <Loader2 size={16} className="spin" /> : <Languages size={16} />}
            {translating ? "Translating..." : "Translate this meeting"}
          </button>
        </div>
      </section>

      {/* ---------- Ask Your Meeting ---------- */}
      <section className="card ask-card">
        <div className="section-head">
          <MessageSquareText size={17} />
          <h3>Ask your meeting</h3>
        </div>

        <div className="ask-input-row">
          <input
            className="input"
            type="text"
            placeholder='e.g. What decisions were made?'
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && handleAsk()}
          />
          <button className="btn btn-primary" onClick={handleAsk} disabled={asking || !question.trim()}>
            {asking ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
            Ask
          </button>
        </div>

        {asking && <p className="hint" style={{ marginTop: 12 }}>Thinking...</p>}

        {askAnswer && (
          <div className="ask-answer">
            <Info size={16} />
            <div>
              <strong>AI answer:</strong> {askAnswer}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default MeetingDetailPage;