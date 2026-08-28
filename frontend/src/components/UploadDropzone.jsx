// UploadDropzone.jsx
// Modern drag-and-drop area for choosing MP3 / WAV / MP4 files.
// Supports clicking to browse and dragging files onto the zone.

import { useRef, useState } from "react";
import { UploadCloud, FileAudio, CheckCircle2, X } from "lucide-react";

import { formatFileSize } from "../utils/format.js";

const ALLOWED_EXTS = ["mp3", "wav", "mp4"];
const ALLOWED_LABEL = "MP3 • WAV • MP4";

function UploadDropzone({ file, onFileChange, error, disabled }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const validateAndSet = (chosenFile) => {
    if (!chosenFile) return;
    const ext = chosenFile.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      onFileChange({ error: "Only MP3, WAV and MP4 files are supported." });
      return;
    }
    onFileChange({ file: chosenFile, error: "" });
  };

  const handleChange = (event) => {
    validateAndSet(event.target.files[0]);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    validateAndSet(event.dataTransfer.files[0]);
  };

  return (
    <div>
      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        {!file ? (
          <>
            <div className="dz-icon">
              <UploadCloud size={28} />
            </div>
            <p className="dz-title">Drag &amp; drop your recording here</p>
            <p className="dz-hint">or <strong>Browse Files</strong></p>
          </>
        ) : (
          <>
            <div className="file-chip">
              <span className="fc-icon">
                <FileAudio size={22} />
              </span>
              <span className="fc-info">
                <span className="fc-name">{file.name}</span>
                <span className="fc-meta">
                  {formatFileSize(file.size)} · {file.type || file.name.split(".").pop().toUpperCase()}
                </span>
              </span>
              {!disabled && (
                <button
                  type="button"
                  className="fc-remove"
                  aria-label="Remove file"
                  onClick={(e) => {
                    e.stopPropagation();
                    onFileChange({ file: null, error: "" });
                  }}
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <span className="dz-hint" style={{ display: "inline-flex", gap: 6, alignItems: "center", fontWeight: 600, color: "#059669" }}>
              <CheckCircle2 size={15} /> File selected
            </span>
          </>
        )}

        <div className="formats-row">
          {ALLOWED_EXTS.map((ext) => (
            <span key={ext} className="format-tag">
              {ext.toUpperCase()}
            </span>
          ))}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".mp3,.wav,.mp4"
        onChange={handleChange}
        style={{ display: "none" }}
      />

      {(error || (!file && null)) && <p className="error-text" style={{ marginTop: 12 }}>{error}</p>}
    </div>
  );
}

export default UploadDropzone;