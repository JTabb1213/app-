import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { getToken, getScoreColor, MOCK_TOKENS } from "../services/mockData"
import { useRealtimePrice } from "../hooks/useRealtimePrice"
import LiveDataPanel from "../components/LiveDataPanel"
import "./CoinPage.css"

const SCORE_LETTER = (score) => {
  if (score >= 90) return "A"
  if (score >= 80) return "A-"
  if (score >= 70) return "B+"
  if (score >= 60) return "B"
  return "C"
}

const RISK_LEVEL = (score) => {
  if (score >= 75) return "Low"
  if (score >= 55) return "Moderate"
  return "High"
}

const CATEGORY_METRICS = {
  security: [
    {
      label: "Holder Diversity",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "On-chain balance spread across top wallets.",
    },
    {
      label: "Top 10 Wallet Concentration",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Percentage held by the biggest 10 addresses.",
    },
    {
      label: "Largest Wallet %",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Single holder concentration risk.",
    },
  ],
  tokenomics: [
    {
      label: "Circulating Supply",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Tokens currently available in the market.",
    },
    {
      label: "Max Supply",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Maximum token issuance cap.",
    },
    {
      label: "Inflation Rate",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Annual supply increase pressure.",
    },
  ],
  community: [
    {
      label: "GitHub Activity",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Code push frequency across repositories.",
    },
    {
      label: "Contributors",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Active developer count.",
    },
    {
      label: "Last Commit",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Recency of the latest code update.",
    },
  ],
  market: [
    {
      label: "Market Cap",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Token valuation in USD.",
    },
    {
      label: "24h Volume",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Trading activity over the past day.",
    },
    {
      label: "Liquidity Status",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Liquidity quality across exchanges.",
    },
  ],
  discourse: [
    {
      label: "Social Sentiment",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Community and social channel signal.",
    },
    {
      label: "Search Interest",
      value: { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Relative attention trends online.",
    },
  ],
}

function CoinPage() {
  const { coinId } = useParams()
  const [openKey, setOpenKey] = useState("security")
  const token = getToken(coinId)
  const { priceData, connectionState, error: wsError } = useRealtimePrice(coinId)

  if (!token) {
    return (
      <div className="page-wrap token-page">
        <Link to="/search" className="back-link">← Back to Search</Link>
        <div className="token-not-found">
          <h2>Token not found</h2>
          <p>We don't have data for "{coinId}" yet.</p>
        </div>
      </div>
    )
  }

  const categories = [
    {
      key: "security",
      title: token.automated.security.label,
      score: token.automated.security.score,
      max: token.automated.security.max,
      metrics: CATEGORY_METRICS.security,
    },
    {
      key: "tokenomics",
      title: token.automated.tokenomics.label,
      score: token.automated.tokenomics.score,
      max: token.automated.tokenomics.max,
      metrics: CATEGORY_METRICS.tokenomics,
    },
    {
      key: "community",
      title: token.automated.community.label,
      score: token.automated.community.score,
      max: token.automated.community.max,
      metrics: CATEGORY_METRICS.community,
    },
    {
      key: "market",
      title: token.automated.market.label,
      score: token.automated.market.score,
      max: token.automated.market.max,
      metrics: CATEGORY_METRICS.market,
    },
    {
      key: "discourse",
      title: token.automated.discourse.label,
      score: token.automated.discourse.score,
      max: token.automated.discourse.max,
      metrics: CATEGORY_METRICS.discourse,
    },
  ]

  const comparison = MOCK_TOKENS.filter((t) => t.id !== token.id).slice(0, 3)
  const trendHistory = [token.overallScore - 6, token.overallScore - 4, token.overallScore - 2, token.overallScore - 1, token.overallScore, token.overallScore, token.overallScore]
  const activityFeed = [
    {
      time: "2h ago",
      title: "Automated signal refreshed",
      description: "Latest market and on-chain indicators were updated.",
    },
    {
      time: "8h ago",
      title: "Manual validation in progress",
      description: "Human review of score operators is underway.",
    },
    {
      time: "1d ago",
      title: "System health checkpoint",
      description: "Development and reporting telemetry were assessed.",
    },
  ]

  const minTrend = Math.min(...trendHistory)
  const maxTrend = Math.max(...trendHistory)
  const trendCoords = trendHistory.map((value, index) => {
    const x = index * 18
    const y = 90 - ((value - minTrend) / (maxTrend - minTrend || 1)) * 70
    return { x, y, value }
  })
  const linePath = trendCoords
    .map((coord, index) => `${index === 0 ? "M" : "L"} ${coord.x} ${coord.y}`)
    .join(" ")
  const areaPath = `${linePath} L ${trendCoords[trendCoords.length - 1].x} 90 L ${trendCoords[0].x} 90 Z`

  const scorePct = Math.max(0, Math.min(token.overallScore, 100))
  const scoreRadius = 52
  const scoreCircumference = 2 * Math.PI * scoreRadius
  const scoreOffset = scoreCircumference - (scorePct / 100) * scoreCircumference
  const scoreRingColor = token.overallScore >= 75 ? "#22c55e" : token.overallScore >= 60 ? "#eab308" : "#ef4444"

  return (
    <div className="page-wrap token-page dashboard-shell">
      <section className="token-summary fade-in fade-in-2">
        <div className="token-summary-left">
          <div className="token-path">
            <Link to="/" className="token-breadcrumb">Dashboard</Link>
            <span className="token-separator">/</span>
            <span>{token.name}</span>
          </div>
          <h1>{token.name}</h1>
          <span className="token-subtitle">{token.ticker} · Utility coin intelligence</span>
        </div>
        <div className="token-summary-right">
          <div className="token-score-hero">
            <div className="token-score-ring">
              <svg viewBox="0 0 120 120" className="score-ring-svg">
                <circle className="score-ring-bg" cx="60" cy="60" r={scoreRadius} strokeWidth="10" />
                <circle
                  className="score-ring-fg"
                  cx="60"
                  cy="60"
                  r={scoreRadius}
                  strokeWidth="10"
                  style={{
                    stroke: scoreRingColor,
                    strokeDasharray: scoreCircumference,
                    strokeDashoffset: scoreOffset,
                  }}
                />
              </svg>
              <span className="token-score-large">{token.overallScore}</span>
            </div>
            <div className="token-score-copy">
              <span className="token-score-rating">{SCORE_LETTER(token.overallScore)} Rating</span>
              <span className="token-score-caption">Overall CCS Score</span>
            </div>
          </div>
        </div>
      </section>

      <section className="coin-kpi-row fade-in fade-in-2">
        <div className="kpi-card">
          <span className="kpi-label">CCS Score</span>
          <span className="kpi-value">{token.overallScore}<small>/100</small></span>
          <span className="kpi-meta">Grade {SCORE_LETTER(token.overallScore)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Automated Signal</span>
          <span className="kpi-value">{token.automated.total}<small>/75</small></span>
          <span className="kpi-meta">System-generated score</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Manual Validation</span>
          <span className="kpi-value">{token.manual ? `${token.manual.total}/25` : "In Progress"}</span>
          <span className="kpi-meta">Human validation</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Risk Level</span>
          <span className={`kpi-value risk-${RISK_LEVEL(token.overallScore).toLowerCase()}`}>{RISK_LEVEL(token.overallScore)}</span>
          <span className="kpi-meta">Interpretive signal</span>
        </div>
      </section>

      <main className="coin-grid fade-in fade-in-3">
        <div className="primary-column">

          {/* Live price, volume & candle chart */}
          <LiveDataPanel
            coinId={coinId}
            priceData={priceData}
            connectionState={connectionState}
            wsError={wsError}
          />

          <section className="panel card-panel">
            <div className="panel-header">
              <div>
                <h2>Score Breakdown</h2>
                <p>Deep dive into automated category scores and sub-metric visibility.</p>
              </div>
            </div>
            <div className="accordion">
              {categories.map((cat) => {
                const pct = Math.round((cat.score / cat.max) * 100)
                const open = openKey === cat.key
                return (
                  <div className={`accordion-item ${open ? "open" : ""}`} key={cat.key}>
                    <button className="accordion-header" type="button" onClick={() => setOpenKey(open ? null : cat.key)}>
                      <div>
                        <div className="accordion-title">{cat.title}</div>
                        <div className="accordion-subtitle">{cat.score} / {cat.max}</div>
                      </div>
                      <span className="accordion-icon">▼</span>
                    </button>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <div className={`accordion-panel ${open ? "expanded" : ""}`}>
                      <div className="metric-list">
                        {cat.metrics.map((metric) => {
                          const isPending = metric.value && metric.value.label
                          return (
                            <div className="metric-row" key={metric.label}>
                              <div>
                                <div className="metric-name">{metric.label}</div>
                                <div className="metric-desc">{metric.description}</div>
                              </div>
                              <div className={`metric-value ${isPending ? "metric-state" : ""}`}>
                                <div>{isPending ? metric.value.label : metric.value}</div>
                                {isPending ? <div className="metric-value-detail">{metric.value.subtext}</div> : null}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="panel card-panel trend-card">
            <div className="panel-header">
              <div>
                <h2>CCS Score Trend</h2>
                <p>Score movement based on the latest available data signals.</p>
              </div>
            </div>
            <div className="trend-chart">
              <svg viewBox="0 0 120 100" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="trendGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#4da7ff" />
                    <stop offset="100%" stopColor="#9f7cff" />
                  </linearGradient>
                  <linearGradient id="trendArea" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="rgba(77, 167, 255, 0.22)" />
                    <stop offset="100%" stopColor="rgba(159, 124, 255, 0)" />
                  </linearGradient>
                </defs>
                {[20, 40, 60, 80].map((y) => (
                  <line key={y} x1="0" y1={y} x2="120" y2={y} stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
                ))}
                <path d={areaPath} fill="url(#trendArea)" stroke="none" />
                <path d={linePath} fill="none" stroke="url(#trendGradient)" strokeWidth="3" strokeLinecap="round" />
                {trendCoords.map((point, index) => (
                  <circle key={index} cx={point.x} cy={point.y} r="2.2" fill="rgba(255,255,255,0.95)" />
                ))}
              </svg>
            </div>
            <div className="trend-meta">
              <span>Latest score: {token.overallScore}</span>
              <span>Week high: {Math.max(...trendHistory)}</span>
            </div>
          </section>

          <div className="split-cards">
            <section className="panel small-panel">
              <div className="panel-header">
                <h3>Market Intelligence</h3>
              </div>
              <div className="list-group">
                <div className="list-item"><span>Market Cap</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
                <div className="list-item"><span>24h Volume</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
                <div className="list-item"><span>Liquidity Status</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
              </div>
            </section>
            <section className="panel small-panel">
              <div className="panel-header">
                <h3>Tokenomics</h3>
              </div>
              <div className="list-group">
                <div className="list-item"><span>Circulating Supply</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
                <div className="list-item"><span>Max Supply</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
                <div className="list-item"><span>Inflation Indicator</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
              </div>
            </section>
          </div>
        </div>

        <aside className="secondary-column">
          <section className="panel signal-panel">
            <div className="panel-header">
              <h2>Risk Signals</h2>
            </div>
            <div className="signal-list">
              <div className="signal-item warning">⚠ Whale concentration: Unverified</div>
              <div className="signal-item warning">⚠ Liquidity signal: Limited coverage</div>
              <div className="signal-item safe">✅ Developer activity: Positive</div>
            </div>
          </section>

          <section className="panel dev-panel">
            <div className="panel-header">
              <h2>Development</h2>
            </div>
            <div className="dev-list">
              <div className="dev-row"><span>GitHub Activity</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
              <div className="dev-row"><span>Contributors</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
              <div className="dev-row"><span>Last Commit</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
            </div>
          </section>

          <section className="panel compare-panel">
            <div className="panel-header">
              <h2>Comparison</h2>
            </div>
            <div className="compare-list">
              {comparison.map((item) => (
                <div className="compare-row" key={item.id}>
                  <span>{item.name}</span>
                  <strong>{item.overallScore}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="panel activity-panel">
            <div className="panel-header">
              <h2>System Activity</h2>
            </div>
            <div className="activity-list">
              {activityFeed.map((event, index) => (
                <div className="activity-item" key={index}>
                  <span className="activity-time">{event.time}</span>
                  <div>
                    <div className="activity-title">{event.title}</div>
                    <div className="activity-desc">{event.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </main>
    </div>
  )
}

export default CoinPage
