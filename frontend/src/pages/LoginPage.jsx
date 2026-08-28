// LoginPage.jsx
// Clean centered authentication card.
// Logs a real user in through the Flask backend (session cookie).

import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LogIn, Loader2 } from "lucide-react";

import Logo from "../components/Logo.jsx";
import Alert from "../components/Alert.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getErrorMessage } from "../services/api.js";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const registeredEmail = location.state?.registered;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!EMAIL_PATTERN.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    if (password.length < 4) {
      setError("Your password must be at least 4 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await login({ email, password });
      const redirectTo = location.state?.from || "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Could not sign you in. Please try again."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <Logo />
        </div>

        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-sub">Sign in to your meeting workspace</p>

        {registeredEmail && (
          <Alert type="success" message={`Account created for ${registeredEmail}. Please sign in.`} />
        )}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="label" htmlFor="email">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="field">
            <label className="label" htmlFor="password">Password</label>
            <input
              id="password"
              className="input"
              type="password"
              placeholder="Your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && <Alert type="error" message={error} />}

          <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={submitting}>
            {submitting ? <Loader2 size={17} className="spin" /> : <LogIn size={17} />}
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="auth-footer">
          New here? <Link to="/signup" className="link">Create Account</Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;