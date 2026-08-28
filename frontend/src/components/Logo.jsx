// Logo.jsx
// The TalkToText Pro brand mark + wordmark.

import { Link } from "react-router-dom";
import { Mic } from "lucide-react";

function Logo({ to = "/", light = false }) {
  return (
    <Link to={to} className="brand" style={light ? { color: "#fff" } : undefined}>
      <span className="brand-mark">
        <Mic size={18} />
      </span>
      <span className="brand-name">
        TalkToText <span>Pro</span>
      </span>
    </Link>
  );
}

export default Logo;