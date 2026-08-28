// Navbar.jsx
// Sticky glass navigation with desktop links and a mobile menu.
// The links change based on the real login state.

import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, FolderOpen, Plus, LogOut, Home, Menu, X } from "lucide-react";

import Logo from "./Logo.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const LOGGED_IN_LINKS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/meetings", label: "Meetings", icon: FolderOpen },
  { to: "/transcribe", label: "Analyze Meeting", icon: Plus },
];

const LOGGED_OUT_LINKS = [
  { to: "/", label: "Home", icon: Home },
];

function Navbar() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Close the mobile menu whenever the route changes.
  const closeMenu = () => setMenuOpen(false);

  const navLinks = user ? LOGGED_IN_LINKS : LOGGED_OUT_LINKS;

  const handleLogout = async () => {
    closeMenu();
    await logout();
    navigate("/", { replace: true });
  };

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "G";

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Logo />

        <nav className="nav-links">
          {navLinks.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="nav-actions">
          {user ? (
            <>
              <span className="user-chip hide-sm">
                <span className="user-avatar">{initials}</span>
                <span className="user-chip-name">{user.name}</span>
              </span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleLogout}
                title="Sign out"
              >
                <LogOut size={15} />
                <span className="hide-sm">Sign out</span>
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="btn btn-ghost btn-sm">
                Sign in
              </NavLink>
              <NavLink to="/signup" className="btn btn-primary btn-sm">
                Get started
              </NavLink>
            </>
          )}

          <button
            className="hamburger"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      <div className={`mobile-menu ${menuOpen ? "open" : ""}`}>
        {navLinks.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={closeMenu}
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
        {!user && (
          <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
            <NavLink to="/login" className="btn btn-secondary btn-sm" onClick={closeMenu}>
              Sign in
            </NavLink>
            <NavLink to="/signup" className="btn btn-primary btn-sm" onClick={closeMenu}>
              Get started
            </NavLink>
          </div>
        )}
        {user && (
          <button
            className="btn btn-ghost btn-sm"
            style={{ justifyContent: "flex-start", marginTop: 8 }}
            onClick={handleLogout}
          >
            <LogOut size={15} />
            Sign out ({user.name})
          </button>
        )}
      </div>
    </header>
  );
}

export default Navbar;