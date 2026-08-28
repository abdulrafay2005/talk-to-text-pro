// Alert.jsx
// Polished error / info banner with an optional "Try again" button.

import { AlertCircle, Info, RotateCcw } from "lucide-react";

function Alert({ type = "error", message, onRetry, retryLabel = "Try again" }) {
  if (!message) return null;

  const Icon = type === "error" ? AlertCircle : Info;

  return (
    <div className={`alert alert-${type}`} role="alert">
      <Icon size={17} />
      <span>{message}</span>
      {onRetry && (
        <button className="btn btn-ghost btn-sm alert-actions" onClick={onRetry}>
          <RotateCcw size={13} />
          {retryLabel}
        </button>
      )}
    </div>
  );
}

export default Alert;