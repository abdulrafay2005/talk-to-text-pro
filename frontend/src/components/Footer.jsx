// Footer.jsx
// Small site footer used on the landing page.

import Logo from "./Logo.jsx";

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <Logo />
        <span>
          Built with React, Flask, faster-whisper &amp; Gemini
        </span>
        <span>© {new Date().getFullYear()} TalkToText Pro</span>
      </div>
    </footer>
  );
}

export default Footer;