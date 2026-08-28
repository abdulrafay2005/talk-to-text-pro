import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, useLocation } from "react-router-dom";

import App from "./App.jsx";
import { MeetingProvider } from "./context/MeetingContext.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import "./index.css";

// Scroll to the top of the page on every route change.
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ScrollToTop />
      <AuthProvider>
        <MeetingProvider>
          <App />
        </MeetingProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);