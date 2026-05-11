import { Link } from "react-router-dom"
import "./Footer.css"

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="footer-logo"><span className="footer-c">C</span><span className="footer-c">C</span><span className="footer-s">S</span><span className="footer-dot">.</span></span>
          <p className="footer-tagline">Utility. Verified. Rated.</p>
        </div>
        <div className="footer-links">
          <Link to="/">Home</Link>
          <Link to="/search">Search</Link>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/about">Methodology</Link>
        </div>
        <p className="footer-disclaimer">
          CCS scores are for informational purposes only and do not constitute financial advice.
        </p>
      </div>
    </footer>
  )
}

export default Footer
