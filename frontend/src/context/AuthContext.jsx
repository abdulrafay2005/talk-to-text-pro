// AuthContext.jsx
// Real authentication backed by the Flask API + MongoDB Atlas.
//
// The session lives in an HttpOnly session cookie (set by the backend),
// so nothing personal is ever saved in localStorage and passwords are
// never sent to the browser. On app start we call GET /api/auth/me to
// restore the session.

import { createContext, useContext, useEffect, useState } from "react";

import { getCurrentUser, login as apiLogin, logout as apiLogout, register as apiRegister } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // When the app starts, ask the backend who is logged in (if anyone).
  useEffect(() => {
    let mounted = true;
    getCurrentUser()
      .then((data) => {
        if (mounted) setUser(data);
      })
      .catch(() => {
        if (mounted) setUser(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const login = async ({ email, password }) => {
    const data = await apiLogin({ email, password });
    setUser(data.user);
    return data.user;
  };

  const signup = async ({ name, email, password }) => {
    const data = await apiRegister({ name, email, password });
    return data.user;
  };

  const logout = async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Hook that pages use to reach the current user / auth actions.
export function useAuth() {
  return useContext(AuthContext);
}