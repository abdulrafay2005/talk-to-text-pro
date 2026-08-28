import { Route, Routes, Link } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignUpPage from "./pages/SignUpPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import TranscribePage from "./pages/TranscribePage.jsx";
import ProcessingPage from "./pages/ProcessingPage.jsx";
import MeetingsPage from "./pages/MeetingsPage.jsx";
import MeetingDetailPage from "./pages/MeetingDetailPage.jsx";
import SharePage from "./pages/SharePage.jsx";

function NotFound() {
  return (
    <div className="page page-fade" style={{ textAlign: "center" }}>
      <h1 className="dash-title">Page not found</h1>
      <p className="dash-sub" style={{ margin: "12px 0 24px" }}>
        The page you are looking for does not exist.
      </p>
      <Link to="/" className="btn btn-primary">
        Go home
      </Link>
    </div>
  );
}

function App() {
  return (
    <div className="app">
      <Navbar />

      <main className="container" style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/transcribe"
            element={
              <ProtectedRoute>
                <TranscribePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/processing"
            element={
              <ProtectedRoute>
                <ProcessingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings"
            element={
              <ProtectedRoute>
                <MeetingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings/:id"
            element={
              <ProtectedRoute>
                <MeetingDetailPage />
              </ProtectedRoute>
            }
          />
          <Route path="/share/:token" element={<SharePage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;