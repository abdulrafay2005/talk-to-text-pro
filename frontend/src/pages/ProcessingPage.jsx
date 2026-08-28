import { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Check, Loader2, Mic } from "lucide-react";

import Alert from "../components/Alert.jsx";
import { uploadMeeting, getErrorMessage } from "../services/api.js";
import { useMeetings } from "../context/MeetingContext.jsx";

const STEPS = [
  { label: "Upload", message: "Uploading your meeting..." },
  { label: "Transcribe", message: "Transcribing the conversation..." },
  { label: "Clean", message: "Cleaning the transcript..." },
  { label: "Translate", message: "Translating your meeting..." },
  { label: "Analyze", message: "Understanding the discussion..." },
  { label: "Save", message: "Extracting decisions and action items..." },
  { label: "Complete", message: "Preparing your meeting intelligence..." },
];

const startedUploadIds = new Set();


function playCompletionSound() {
  try {
    const AudioContext =
      window.AudioContext || window.webkitAudioContext;

    if (!AudioContext) {
      console.warn("Web Audio API is not supported by this browser.");
      return;
    }

    const audioContext = new AudioContext();

    const playTone = (frequency, startTime, duration) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(
        frequency,
        startTime
      );

      // Start quietly and fade out smoothly.
      gainNode.gain.setValueAtTime(0.0001, startTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.18,
        startTime + 0.02
      );
      gainNode.gain.exponentialRampToValueAtTime(
        0.0001,
        startTime + duration
      );

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.start(startTime);
      oscillator.stop(startTime + duration);
    };

    const startTime = audioContext.currentTime;

    playTone(1200, startTime, 0.22);
    playTone(860, startTime + 0.18, 0.35);

    // Close the AudioContext after the sound finishes.
    setTimeout(() => {
      audioContext.close().catch(() => {});
    }, 800);
  } catch (error) {
    console.warn("Could not play completion sound:", error);
  }
}

/**
 * Show a browser notification when the meeting finishes.
 *
 * This is optional. If the user hasn't granted notification permission,
 * the function simply does nothing.
 */
function showCompletionNotification() {
  try {
    if (!("Notification" in window)) {
      return;
    }

    if (Notification.permission === "granted") {
      new Notification("TalkToText Pro", {
        body: "Your meeting has finished processing and is ready.",
        icon: "/favicon.ico",
      });
    }
  } catch (error) {
    console.warn(
      "Could not show browser notification:",
      error
    );
  }
}

/**
 * Ask for notification permission.
 *
 * This should only be called from a user interaction, such as clicking
 * the "Analyze meeting" button, because browsers generally block
 * permission requests from automatic/background actions.
 */
export async function requestNotificationPermission() {
  try {
    if (!("Notification" in window)) {
      return;
    }

    if (Notification.permission === "default") {
      await Notification.requestPermission();
    }
  } catch (error) {
    console.warn(
      "Could not request notification permission:",
      error
    );
  }
}

function ProcessingPage() {
  const navigate = useNavigate();
  const {
    pendingUpload,
    clearPendingUpload,
    addMeeting,
  } = useMeetings();

  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [finished, setFinished] = useState(false);

  const timerRef = useRef(null);
  const finishedRef = useRef(false);

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const startUpload = async () => {
    const upload = pendingUpload;

    if (!upload) return;

    try {
      setStep(1);
      setError("");

      console.log("🚀 Starting real backend processing...");

      const result = await uploadMeeting(upload.formData);

      console.log(
        "✅ Backend processing finished:",
        result
      );

      if (result?.success && result?.meeting) {
        if (finishedRef.current) return;

        finishedRef.current = true;

        stopTimer();

        // Mark the processing as complete.
        setStep(STEPS.length - 1);
        setFinished(true);

        // 🔔 PLAY COMPLETION SOUND
        playCompletionSound();

        // 🔔 SHOW DESKTOP NOTIFICATION IF PERMISSION WAS GRANTED
        showCompletionNotification();

        // Add the meeting to the local meeting context.
        addMeeting(result.meeting);

        clearPendingUpload();

        // Give the user a moment to see "Your meeting is ready".
        setTimeout(() => {
          navigate(`/meetings/${result.meeting._id}`, {
            replace: true,
          });
        }, 700);

        return;
      }

      stopTimer();

      setError(
        result?.error ||
          "Something went wrong while analyzing this meeting."
      );
    } catch (err) {
      console.error("❌ Processing failed:", err);

      stopTimer();

      setError(
        getErrorMessage(
          err,
          "Could not analyze this meeting."
        )
      );
    }
  };

  // Animate the pipeline with honest status messages while we wait.
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setStep((current) =>
        Math.min(current + 1, STEPS.length - 1)
      );
    }, 1800);

    return stopTimer;
  }, []);

  // Send the pending upload exactly once.
  useEffect(() => {
    if (!pendingUpload) {
      if (!error && !finishedRef.current) {
        setError(
          "There is nothing to process. Choose a file first."
        );
      }

      return;
    }

    if (startedUploadIds.has(pendingUpload.id)) return;

    startedUploadIds.add(pendingUpload.id);

    startUpload();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Retry the upload after an error.
  const handleRetry = () => {
    setError("");
    setStep(0);

    stopTimer();

    timerRef.current = setInterval(() => {
      setStep((current) =>
        Math.min(current + 1, STEPS.length - 1)
      );
    }, 1800);

    startUpload();
  };

  // If there is nothing waiting, offer a way back.
  if (!pendingUpload && !finished) {
    return (
      <div className="page page-fade processing">
        <div
          className="card section-card"
          style={{ textAlign: "center" }}
        >
          <h2>Nothing to process</h2>

          <p
            className="dash-sub"
            style={{ marginBottom: 20 }}
          >
            Choose an audio or video file to start a new
            analysis.
          </p>

          <Link
            to="/transcribe"
            className="btn btn-primary"
          >
            Analyze a meeting
          </Link>
        </div>
      </div>
    );
  }

  const currentStep = Math.min(
    step,
    STEPS.length - 1
  );

  return (
    <div className="page page-fade processing">
      <div className="proc-icon">
        <Mic size={26} />
      </div>

      <h2>
        {finished
          ? "Your meeting is ready"
          : "Analyzing your meeting"}
      </h2>

      <p className="status-message">
        {finished
          ? "Redirecting you to the results..."
          : STEPS[currentStep].message}
      </p>

      <div className="pipeline">
        {STEPS.map((item, index) => {
          let state = "todo";

          if (finished || index < step) {
            state = "done";
          } else if (index === step) {
            state = "active";
          }

          return (
            <div
              key={item.label}
              className={`pipe-step ${state}`}
            >
              <span className="step-dot">
                {state === "done" ? (
                  <Check size={14} />
                ) : (
                  <span>{index + 1}</span>
                )}
              </span>

              <span className="step-label">
                {item.label}
              </span>

              {state === "active" && (
                <Loader2
                  size={15}
                  className="spin"
                  style={{ marginLeft: "auto" }}
                />
              )}
            </div>
          );
        })}
      </div>

      {error && (
        <div style={{ textAlign: "left" }}>
          <Alert
            type="error"
            message={error}
          />

          <div
            style={{
              display: "flex",
              gap: 10,
              flexWrap: "wrap",
            }}
          >
            <button
              className="btn btn-secondary"
              onClick={handleRetry}
            >
              Try again
            </button>

            <button
              className="btn btn-primary"
              onClick={() =>
                navigate("/transcribe")
              }
            >
              Choose another file
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProcessingPage;
