// ProtectedRoute.jsx
// Wraps pages that should only be seen by logged-in users.
//
//   - while the session is still loading: show a spinner
//   - logged out: redirect to /login (remember where they were going)
//   - logged in: render the page

import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useAuth } from "../context/AuthContext.jsx";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="page page-fade" style={{ textAlign: "center" }}>
        <Loader2 size={26} className="spin" style={{ color: "var(--muted)" }} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export default ProtectedRoute;