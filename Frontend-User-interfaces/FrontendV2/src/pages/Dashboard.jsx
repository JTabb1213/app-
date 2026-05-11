import { Link } from "react-router-dom"
import { MOCK_TOKENS, MOCK_WATCHLIST, getScoreColor } from "../services/mockData"
import "./Dashboard.css"

function Dashboard() {
  const watched = MOCK_WATCHLIST
    .map((id) => MOCK_TOKENS.find((t) => t.id === id))
    .filter(Boolean)

  return (
    <div className="page-wrap dashboard-page">
      <header className="dash-header fade-in fade-in-1">
        <h1>Dashboard</h1>
        <p className="dash-subtitle">Track your watched tokens and monitor score changes.</p>
      </header>

      {/* Chart placeholder */}
      <section className="chart-section fade-in fade-in-2">
        <h2>Score Trends</h2>
        <div className="chart-placeholder">
          <div className="chart-y-axis">
            <span>100</span><span>75</span><span>50</span><span>25</span><span>0</span>
          </div>
          <div className="chart-area">
            {watched.map((token, i) => (
              <div className="chart-bar-group" key={token.id}>
                <div
                  className={`chart-bar ${getScoreColor(token.overallScore)}`}
                  style={{ height: `${token.overallScore}%` }}
                />
                <span className="chart-label">{token.ticker}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Watchlist */}
      <section className="watchlist-section fade-in fade-in-4">
        <h2>Watched Tokens</h2>
        <div className="watchlist">
          {watched.map((token) => (
            <Link
              to={`/token/${token.id}`}
              className="watch-card"
              key={token.id}
            >
              <div className="watch-left">
                <div className="watch-icon" />
                <div className="watch-info">
                  <span className="watch-name">{token.name}</span>
                  <span className="watch-ticker">{token.ticker}</span>
                </div>
              </div>
              <div className="watch-right">
                <span className={`watch-score ${getScoreColor(token.overallScore)}`}>
                  {token.overallScore} <span className="score-of">/ 100</span>
                </span>
                <span className={`status-pill ${token.reviewStatus}`}>
                  {token.reviewStatus === "complete" ? "Reviewed" : "Pending"}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}

export default Dashboard
