import CoinSearch from "../components/CoinSearch"
import { Link } from "react-router-dom"
import "./Home.css"

function Home() {
  return (
    <div className="homepage">
      <section className="hero fade-in fade-in-1">
        <div className="hero-eyebrow">Crypto Currency Solutions</div>
        <h1 className="hero-title">
          Intelligent Coin<br />
          <span className="hero-accent">Intelligence</span>
        </h1>
        <p className="hero-sub">
          Search any cryptocurrency to explore live prices, volume data, candle charts,
          and our in-depth CCS scoring system — all in one place.
        </p>
        <div className="hero-search">
          <CoinSearch placeholder="Search by name, symbol, or ticker…" />
        </div>
      </section>

      <section className="features fade-in fade-in-2">
        <div className="feature-card">
          <div className="feature-icon">📡</div>
          <h3>Live Prices</h3>
          <p>Real-time cross-exchange price comparison streamed via WebSocket. See spreads instantly.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>Volume Analysis</h3>
          <p>Buy/sell pressure breakdown across 5-minute, 30-minute, 4-hour, and 24-hour windows.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📈</div>
          <h3>Candle Charts</h3>
          <p>Interactive OHLC and line charts from 1-day history all the way out to max available data.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🏆</div>
          <h3>CCS Score</h3>
          <p>Our composite scoring model evaluates security, tokenomics, community, market, and discourse.</p>
        </div>
      </section>

      <section className="how-it-works fade-in fade-in-3">
        <h2 className="section-title">How the CCS Score Works</h2>
        <div className="score-breakdown">
          <div className="score-row">
            <span className="score-label">Security</span>
            <div className="score-bar-track"><div className="score-bar-fill" style={{ width: "30%" }} /></div>
            <span className="score-pct">30 pts</span>
          </div>
          <div className="score-row">
            <span className="score-label">Community</span>
            <div className="score-bar-track"><div className="score-bar-fill" style={{ width: "20%" }} /></div>
            <span className="score-pct">20 pts</span>
          </div>
          <div className="score-row">
            <span className="score-label">Market</span>
            <div className="score-bar-track"><div className="score-bar-fill" style={{ width: "20%" }} /></div>
            <span className="score-pct">20 pts</span>
          </div>
          <div className="score-row">
            <span className="score-label">Tokenomics</span>
            <div className="score-bar-track"><div className="score-bar-fill" style={{ width: "15%" }} /></div>
            <span className="score-pct">15 pts</span>
          </div>
          <div className="score-row">
            <span className="score-label">Discourse</span>
            <div className="score-bar-track"><div className="score-bar-fill" style={{ width: "15%" }} /></div>
            <span className="score-pct">15 pts</span>
          </div>
        </div>
      </section>

      <section className="cta-row fade-in fade-in-3">
        <Link to="/search" className="cta-btn">Browse All Coins</Link>
        <Link to="/about" className="cta-btn cta-secondary">Our Methodology</Link>
      </section>
    </div>
  )
}

export default Home
