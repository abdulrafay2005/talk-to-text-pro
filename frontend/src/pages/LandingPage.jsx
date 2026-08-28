// LandingPage.jsx
// The "wow" marketing page with hero, product preview, how it works,
// features, supported formats, CTA and footer.
//
// The AI result preview on this page is STATIC text only - it exists purely
// as a visual demonstration. Real meeting data always comes from the backend.


import { Link } from "react-router-dom";
import {
  Mic,
  Sparkles,
  FileText,
  UploadCloud,
  Brain,
  CheckCircle2,
  Languages,
  Download,
  FolderOpen,
  ArrowRight,
  FileAudio,
  Video,
  Mic2,
  Zap,
} from "lucide-react";

import Footer from "../components/Footer.jsx";

const STEPS = [
  {
    icon: UploadCloud,
    title: "Upload a recording",
    text: "Drop in any MP3, WAV or MP4 file of your meeting. Everything runs on your own machine.",
  },
  {
    icon: Brain,
    title: "AI reads the conversation",
    text: "The transcript is cleaned, optionally translated, then analyzed by a local AI model.",
  },
  {
    icon: FileText,
    title: "Get meeting intelligence",
    text: "Receive a summary, decisions, action items and a PDF report - automatically.",
  },
];

const FEATURES = [
  { icon: Mic, title: "Accurate transcription", text: "faster-whisper converts speech to text with timestamps, 100% offline." },
  { icon: Sparkles, title: "Smart summaries", text: "A local AI summarizes the meeting in clear, factual, simple language." },
  { icon: CheckCircle2, title: "Action items & decisions", text: "Who does what and by when - extracted exactly as people said it." },
  { icon: Languages, title: "Optional translation", text: "Translate your meeting into English, Urdu, Spanish, French and more." },
  { icon: Download, title: "PDF export", text: "One click turns every meeting into a clean, shareable PDF report." },
  { icon: FolderOpen, title: "Meeting history", text: "Every meeting is saved and searchable so you never lose context." },
];

function LandingPage() {
  return (
    <div className="page-fade">
      {/* ---------- Hero ---------- */}
      <section className="hero">
        <div className="container hero-inner">
          <div>
            <span className="hero-badge">
              <Zap size={14} />
              AI Meeting Assistant
            </span>

            <h1 className="hero-title">
              Turn every meeting into <span className="grad">actionable intelligence.</span>
            </h1>

            <p className="hero-sub">
              Upload your meeting recording and let AI transform conversations
              into clear summaries, decisions, and action items.
            </p>

            <div className="hero-actions">
              <Link to="/transcribe" className="btn btn-primary btn-lg">
                <Mic2 size={17} />
                Start Analyzing
              </Link>
              <a href="#how-it-works" className="btn btn-secondary btn-lg">
                See How It Works
              </a>
            </div>

            <div className="hero-trust">
              <span>
                <CheckCircle2 size={14} color="#10b981" />
                Runs locally
              </span>
              <span>
                <CheckCircle2 size={14} color="#10b981" />
                No paid APIs
              </span>
              <span>
                <CheckCircle2 size={14} color="#10b981" />
                PDF export
              </span>
            </div>
          </div>

          {/* Static demo preview (not real data) */}
          <div className="hero-preview">
            <div className="product-preview">
              <div className="product-window">
                <div className="window-bar">
                  <div className="window-dots">
                    <span className="window-dot window-dot-red" />
                    <span className="window-dot window-dot-amber" />
                    <span className="window-dot window-dot-green" />
                  </div>
                  <span className="window-title">TalkToText Pro</span>
                  <span className="product-status">
                    <span className="live-dot" />
                    AI Analysis
                  </span>
                </div>

                <div className="product-header">
                  <div>
                    <h3>Project Planning — Team Meeting</h3>
                    <p>Today · 42 min · 4 speakers</p>
                  </div>
                  <span className="analyzed-badge">
                    <CheckCircle2 size={13} />
                    Analyzed
                  </span>
                </div>

                <div className="analysis-flow">
                  <span className="analysis-step">
                    <FileText size={13} />
                    Transcript
                  </span>
                  <span className="analysis-line" />
                  <span className="analysis-step">
                    <Brain size={13} />
                    AI Analysis
                  </span>
                  <span className="analysis-line" />
                  <span className="analysis-step active">
                    <Sparkles size={13} />
                    Meeting Intelligence
                  </span>
                </div>

                <div className="preview-content">
                  <div className="summary-panel">
                    <h4>Meeting Summary</h4>
                    <ul>
                      <li>Team finalized the API endpoints and data flow.</li>
                      <li>Database schema agreed on by end of the week.</li>
                      <li>Frontend auth connects over the next two days.</li>
                    </ul>
                  </div>

                  <div className="action-panel">
                    <h4>Action Items</h4>
                    <div className="action-row">
                      {/* <span className="mini-avatar">A</span> */}
                      <div>
                        <strong>Finalize API endpoints</strong>
                        <span>Ali · Friday</span>
                      </div>
                    </div>
                    <div className="action-row">
                      {/* <span className="mini-avatar">S</span> */}
                      <div>
                        <strong>Prepare database schema</strong>
                        <span>Sara · Thursday</span>
                      </div>
                    </div>
                    <div className="action-row">
                      {/* <span className="mini-avatar">A</span> */}
                      <div>
                        <strong>Connect frontend auth</strong>
                        <span>Ahmed · Next week</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="preview-metrics">
                  <div className="preview-metric">
                    <strong>42</strong>
                    <span>min</span>
                  </div>
                  <div className="preview-metric">
                    <strong>4</strong>
                    <span>speakers</span>
                  </div>
                  <div className="preview-metric">
                    <strong>28%</strong>
                    <span>time saved</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section id="how-it-works" className="section">
        <div className="container">
          <span className="section-tag">How it works</span>
          <h2 className="section-title center">From audio file to action plan in seconds</h2>
          <p className="section-sub center">
            Three simple steps. No configuration, no accounts, no cloud uploads.
          </p>

          <div className="steps-grid">
            {STEPS.map((step, index) => (
              <div key={step.title} className="step-card">
                <span className="step-num">0{index + 1}</span>
                <step.icon size={22} color="#6366f1" style={{ marginBottom: 14 }} />
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Features ---------- */}
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <span className="section-tag">Features</span>
          <h2 className="section-title center">Everything a meeting assistant should do</h2>

          <div className="features-grid">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="feature-card">
                <span className="feature-icon">
                  <Icon size={20} />
                </span>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Supported formats ---------- */}
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="formats-band">
            <span className="format-item">
              <span className="fi-icon"><FileAudio size={18} /></span>
              MP3
            </span>
            <span className="format-item">
              <span className="fi-icon"><Mic size={18} /></span>
              WAV
            </span>
            <span className="format-item">
              <span className="fi-icon"><Video size={18} /></span>
              MP4
            </span>
            <span className="muted">Unsupported files are rejected with a clear error.</span>
          </div>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="cta-band">
            <h2>Ready to understand your next meeting?</h2>
            <p>Upload a recording and get your AI meeting intelligence right now.</p>
            <Link to="/transcribe" className="btn btn-light btn-lg">
              <ArrowRight size={17} />
              Start analyzing
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}

export default LandingPage;