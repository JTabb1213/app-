import { useState } from "react"
import { Link, useLocation } from "react-router-dom"
import CoinSearch from "./CoinSearch"
import "./Navbar.css"

function Navbar() {
  const { pathname } = useLocation()

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <span className="brand-c">C</span>
        <span className="brand-c">C</span>
        <span className="brand-s">S</span>
        <span className="brand-dot">.</span>
      </Link>

      <div className="navbar-search">
        <CoinSearch placeholder="Search coins…" />
      </div>

      <div className="navbar-links">
        <Link to="/" className={`nav-link${pathname === "/" ? " active" : ""}`}>Home</Link>
        <Link to="/search" className={`nav-link${pathname === "/search" ? " active" : ""}`}>Search</Link>
        <Link to="/dashboard" className={`nav-link${pathname === "/dashboard" ? " active" : ""}`}>Dashboard</Link>
        <Link to="/about" className={`nav-link${pathname === "/about" ? " active" : ""}`}>Methodology</Link>
      </div>
    </nav>
  )
}

export default Navbar
