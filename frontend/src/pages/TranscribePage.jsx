// TranscribePage.jsx
// Beautiful drag-and-drop upload screen.
//
// The selected file is sent to the REAL backend with FormData. The actual
// upload + processing happens on the /processing page, so the file details
// are passed through the meetings context (never lost during navigation).

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";

import UploadDropzone from "../components/UploadDropzone.jsx";
import Alert from "../components/Alert.jsx";
import { useMeetings } from "../context/MeetingContext.jsx";

const LANGUAGES = [
  { code: "", label: "No Translation" },
  { code: "en", label: "English" },
  { code: "ur", label: "Urdu" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "ar", label: "Arabic" },
  { code: "hi", label: "Hindi" },
  { code: "de", label: "German" },
];

function TranscribePage() {
  const navigate = useNavigate();
  const { setPendingUpload } = useMeetings();

  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [translateTo, setTranslateTo] = useState("");
  const [dropError, setDropError] = useState("");

  // UploadDropzone uses this to update the selected file.
  const handleFileChange = ({ file: nextFile, error }) => {
    setDropError(error || "");
    setFile(nextFile);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setDropError("");

    if (!file) {
      setDropError("Please choose a file first.");
      return;
    }

    // Build the real FormData sent to the Flask backend.
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title.trim() || "Untitled Meeting");
    if (translateTo) {
      formData.append("translate_to", translateTo);
    }

    // Pass the upload to the processing page through the context.
    // A unique id prevents the same upload from ever being sent twice.
    setPendingUpload({
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      formData,
      title: title.trim() || "Untitled Meeting",
      translateTo,
    });
    navigate("/processing");
  };

  return (
    <div className="page page-fade">
      <div className="upload-layout">
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <span className="hero-badge" style={{ marginBottom: 14 }}>
            <Sparkles size={14} />
            Analyze your meeting
          </span>
          <h1 className="dash-title">Upload a recording</h1>
          <p className="dash-sub">
            MP3, WAV or MP4. The AI does the rest.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="card upload-form">
          <UploadDropzone
            file={file}
            onFileChange={handleFileChange}
            error={dropError}
          />

          <div className="field">
            <label className="label" htmlFor="title">Meeting title (optional)</label>
            <input
              id="title"
              className="input"
              type="text"
              placeholder="e.g. Project kickoff meeting"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>

          <div className="field">
            <label className="label" htmlFor="translate">Translation</label>
            <select
              id="translate"
              className="select"
              value={translateTo}
              onChange={(event) => setTranslateTo(event.target.value)}
            >
              {LANGUAGES.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.label}
                </option>
              ))}
            </select>
            <p className="hint" style={{ marginTop: 6 }}>
              Select a language to also get a translated transcript. "No Translation" keeps your meeting in its original language.
            </p>
          </div>

          {dropError && <Alert type="error" message={dropError} />}

          <button className="btn btn-primary btn-block btn-lg" type="submit" style={{ marginTop: 8 }}>
            Analyze Meeting
            <ArrowRight size={17} />
          </button>
        </form>
      </div>
    </div>
  );
}

export default TranscribePage;