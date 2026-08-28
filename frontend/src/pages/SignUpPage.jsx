// SignUpPage.jsx
// Clean centered sign-up card.
// Creates a REAL account in MongoDB Atlas through the Flask backend.

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { UserPlus, Loader2 } from "lucide-react";

import Logo from "../components/Logo.jsx";
import Alert from "../components/Alert.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getErrorMessage } from "../services/api.js";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function SignUpPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Please enter your name.");
      return;
    }
    if (!EMAIL_PATTERN.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    if (password.length < 4) {
      setError("Your password must be at least 4 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await signup({ name, email, password });
      navigate("/login", { state: { registered: email } });
    } catch (err) {
      setError(getErrorMessage(err, "Could not create your account. Please try again."));
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

        <h1 className="auth-title">Create your account</h1>
        <p className="auth-sub">Start turning meetings into intelligence</p>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="label" htmlFor="name">Name</label>
            <input
              id="name"
              className="input"
              type="text"
              placeholder="Your name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="name"
            />
          </div>

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
              placeholder="At least 4 characters"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
            />
          </div>

          <div className="field">
            <label className="label" htmlFor="confirm">Confirm Password</label>
            <input
              id="confirm"
              className="input"
              type="password"
              placeholder="Repeat your password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              autoComplete="new-password"
            />
          </div>

          {error && <Alert type="error" message={error} />}

          <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={submitting}>
            {submitting ? <Loader2 size={17} className="spin" /> : <UserPlus size={17} />}
            {submitting ? "Creating account..." : "Sign Up"}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login" className="link">Sign In</Link>
        </p>
      </div>
    </div>
  );
}

export default SignUpPage;