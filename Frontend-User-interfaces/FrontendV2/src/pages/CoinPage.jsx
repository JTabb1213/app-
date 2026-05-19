import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { getRating, getMarketData, getNews } from "../services/api"
import { useRealtimePrice } from "../hooks/useRealtimePrice"
import LiveDataPanel from "../components/LiveDataPanel"
import MarketData from "../components/MarketData"
import RecentNews from "../components/RecentNews"
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

// Returns method-aware security metric labels for the score breakdown panel.
// diversity_method comes from rating.security_transparency.metrics.diversity_method
function getSecurityMetrics(secMetrics) {
  const method = secMetrics?.diversity_method || "token_holders"

  if (method === "hashrate") {
    return [
      {
        label: "Nakamoto Coefficient",
        value: secMetrics?.nakamoto_coefficient != null
          ? { label: String(secMetrics.nakamoto_coefficient), subtext: "pools needed to reach 51% hashrate" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Minimum number of mining pools that could collude to 51%-attack the network.",
      },
      {
        label: "Largest Pool Share",
        value: secMetrics?.largest_pool_pct != null
          ? { label: `${secMetrics.largest_pool_pct.toFixed(1)}%`, subtext: "of total hashrate" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Single mining pool concentration risk.",
      },
      {
        label: "Active Mining Pools",
        value: secMetrics?.pool_count != null
          ? { label: String(secMetrics.pool_count), subtext: "pools observed (7-day window)" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Breadth of mining competition.",
      },
    ]
  }

  if (method === "validator") {
    return [
      {
        label: "Nakamoto Coefficient",
        value: secMetrics?.nakamoto_coefficient != null
          ? { label: String(secMetrics.nakamoto_coefficient), subtext: "entities to reach 33% stake" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Minimum staking entities needed to threaten PoS finality.",
      },
      {
        label: "Largest Entity Stake",
        value: secMetrics?.largest_entity_pct != null
          ? { label: `${secMetrics.largest_entity_pct.toFixed(1)}%`, subtext: "of all staked ETH" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Single-entity dominance risk (e.g. Lido, Coinbase).",
      },
      {
        label: "Active Staking Entities",
        value: secMetrics?.entity_count != null
          ? { label: String(secMetrics.entity_count), subtext: "named operators" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Number of distinct staking entities observed.",
      },
    ]
  }

  if (method === "vesting") {
    return [
      {
        label: "Insider Allocation",
        value: secMetrics?.insider_pct != null
          ? { label: `${secMetrics.insider_pct.toFixed(1)}%`, subtext: "team / VC / foundation" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "Total supply allocated to insiders at genesis.",
      },
      {
        label: "Circulating Ratio",
        value: secMetrics?.circulating_ratio != null
          ? { label: `${(secMetrics.circulating_ratio * 100).toFixed(1)}%`, subtext: "of total supply in circulation" }
          : { label: "Data Pending", subtext: "Source integration in progress." },
        description: "How much of the total supply has been distributed to the public.",
      },
      {
        label: "Risk Flags",
        value: { label: secMetrics?.risk_flags?.length > 0 ? `${secMetrics.risk_flags.length} flagged` : "None", subtext: secMetrics?.risk_flags?.[0] || "" },
        description: "Notable vesting or centralisation risks from public research.",
      },
    ]
  }

  // Default: token_holders (ERC-20 richlist)
  return [
    {
      label: "Holder Diversity",
      value: secMetrics?.top_10_pct != null
        ? { label: `${secMetrics.top_10_pct.toFixed(1)}% in top 10`, subtext: "on-chain concentration" }
        : { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Percentage of supply held by the top 10 wallet addresses.",
    },
    {
      label: "Top 10 Wallet Concentration",
      value: secMetrics?.top_10_pct != null
        ? { label: `${secMetrics.top_10_pct.toFixed(1)}%`, subtext: "of circulating supply" }
        : { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Percentage held by the biggest 10 addresses.",
    },
    {
      label: "Largest Wallet %",
      value: secMetrics?.largest_wallet_pct != null
        ? { label: `${secMetrics.largest_wallet_pct.toFixed(1)}%`, subtext: "single holder" }
        : { label: "Data Pending", subtext: "Source integration in progress." },
      description: "Single holder concentration risk.",
    },
  ]
}

function pending() {
  return { label: "Data Pending", subtext: "Source integration in progress." }
}

function getTokenomicsMetrics(m) {
  return [
    {
      label: "Inflation Potential",
      value: m?.inflation_potential_pct != null
        ? { label: `${m.inflation_potential_pct.toFixed(1)}%`, subtext: "of max supply remaining" }
        : pending(),
      description: "Percentage of max supply not yet issued.",
    },
    {
      label: "Max Supply Cap",
      value: m?.has_max_supply != null
        ? { label: m.has_max_supply ? "Yes" : "No cap", subtext: m.has_max_supply ? "Fixed issuance limit" : "Uncapped inflation possible" }
        : pending(),
      description: "Whether a hard maximum supply limit exists.",
    },
  ]
}

function getCommunityMetrics(m) {
  return [
    {
      label: "GitHub Activity",
      value: m?.delta_commits != null
        ? { label: `+${m.delta_commits} commits`, subtext: "since last cycle" }
        : pending(),
      description: "New commits pushed since the previous scoring cycle.",
    },
    {
      label: "Contributors",
      value: m?.contributor_count != null
        ? { label: `${m.contributor_count}`, subtext: "active developers" }
        : pending(),
      description: "Active developer count across tracked repositories.",
    },
  ]
}

function getDiscourseMetrics(m) {
  return [
    {
      label: "Reddit Sentiment",
      value: m?.reddit_compound != null
        ? {
          label: m.reddit_compound > 0.1 ? "Positive" : m.reddit_compound < -0.1 ? "Negative" : "Neutral",
          subtext: `score ${m.reddit_compound.toFixed(2)}`
        }
        : pending(),
      description: "Compound sentiment score from recent Reddit activity.",
    },
    {
      label: "Search Interest",
      value: m?.search_interest != null
        ? { label: `${m.search_interest}/100`, subtext: "Google Trends index" }
        : pending(),
      description: "Relative search volume trend over the past 7 days.",
    },
  ]
}

function CoinPage() {
  const { coinId } = useParams()
  const [openKey, setOpenKey] = useState("security")
  const { priceData, connectionState, error: wsError } = useRealtimePrice(coinId)

  // ── Live data from API (three independent calls) ───────────────────────────
  const [rating, setRating] = useState(null)
  const [marketData, setMarketData] = useState(null)
  const [news, setNews] = useState(null)
  const [ratingLoading, setRatingLoading] = useState(true)
  const [marketLoading, setMarketLoading] = useState(true)
  const [newsLoading, setNewsLoading] = useState(true)

  useEffect(() => {
    setRatingLoading(true)
    getRating(coinId)
      .then(setRating)
      .catch(() => setRating(null))
      .finally(() => setRatingLoading(false))
  }, [coinId])

  useEffect(() => {
    setMarketLoading(true)
    getMarketData(coinId)
      .then(setMarketData)
      .catch(() => setMarketData(null))
      .finally(() => setMarketLoading(false))
  }, [coinId])

  useEffect(() => {
    setNewsLoading(true)
    getNews(coinId)
      .then(setNews)
      .catch(() => setNews(null))
      .finally(() => setNewsLoading(false))
  }, [coinId])

  // ── Derived display values (no mock fallbacks) ─────────────────────────────
  const displayName = coinId
    ? coinId.charAt(0).toUpperCase() + coinId.slice(1).replace(/-/g, " ")
    : coinId
  const displayTicker = coinId ? coinId.toUpperCase() : ""

  const overallScore = rating?.overall_score ?? 0
  const automatedTotal = rating?.automated_score ?? 0
  const manualTotal = rating?.manual_validation != null ? rating.manual_validation : null
  const riskLevel = rating?.risk_level ?? RISK_LEVEL(overallScore)

  const secScore = rating?.security_transparency?.score ?? 0
  const secMax = rating?.security_transparency?.max ?? 35
  const secMetrics = rating?.security_transparency?.metrics ?? {}
  const tokScore = rating?.tokenomics_utility?.score ?? 0
  const tokMax = rating?.tokenomics_utility?.max ?? 20
  const comScore = rating?.community_dev_activity?.score ?? 0
  const comMax = rating?.community_dev_activity?.max ?? 15
  const disScore = rating?.public_discourse?.score ?? 0
  const disMax = rating?.public_discourse?.max ?? 5

  const categories = [
    { key: "security", title: "Security & Transparency", score: secScore, max: secMax, metrics: getSecurityMetrics(secMetrics) },
    { key: "tokenomics", title: "Tokenomics & Utility", score: tokScore, max: tokMax, metrics: getTokenomicsMetrics(rating?.tokenomics_utility?.metrics ?? {}) },
    { key: "community", title: "Community & Dev Activity", score: comScore, max: comMax, metrics: getCommunityMetrics(rating?.community_dev_activity?.metrics ?? {}) },
    { key: "discourse", title: "Public Discourse", score: disScore, max: disMax, metrics: getDiscourseMetrics(rating?.public_discourse?.metrics ?? {}) },
  ]

  // ── Score history chart ────────────────────────────────────────────────────
  // score_history is [{score, date}, ...] sorted newest-first from the DB trigger.
  // We reverse to get chronological (oldest→newest) for the chart.
  const historyRaw = Array.isArray(rating?.score_history) && rating.score_history.length > 0
    ? [...rating.score_history].sort((a, b) => a.date.localeCompare(b.date))
    : []
  // Always append the current score as the rightmost point
  const trendPoints = [
    ...historyRaw,
    { score: overallScore, date: new Date().toISOString().slice(0, 10) },
  ]
  const trendScores = trendPoints.map(p => p.score)
  const trendDates = trendPoints.map(p => p.date)
  const minTrend = Math.min(...trendScores)
  const maxTrend = Math.max(...trendScores)
  const trendCoords = trendPoints.map((p, i) => {
    const x = trendPoints.length > 1 ? (i / (trendPoints.length - 1)) * 112 + 4 : 60
    const y = 90 - ((p.score - minTrend) / (maxTrend - minTrend || 1)) * 70
    return { x, y, score: p.score, date: p.date }
  })
  const linePath = trendCoords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ")
  const areaPath = `${linePath} L ${trendCoords[trendCoords.length - 1].x} 90 L ${trendCoords[0].x} 90 Z`
  const dotRadius = trendPoints.length > 20 ? 1.2 : trendPoints.length > 10 ? 1.8 : 2.2
  const earliestDate = trendDates[0] ?? "—"
  const latestDate = trendDates[trendDates.length - 1] ?? "—"
  const activityFeed = [
    { time: "2h ago", title: "Automated signal refreshed", description: "Latest market and on-chain indicators were updated." },
    { time: "8h ago", title: "Manual validation in progress", description: "Human review of score operators is underway." },
    { time: "1d ago", title: "System health checkpoint", description: "Development and reporting telemetry were assessed." },
  ]

  const scorePct = Math.max(0, Math.min(overallScore, 100))
  const scoreRadius = 52
  const scoreCircumference = 2 * Math.PI * scoreRadius
  const scoreOffset = scoreCircumference - (scorePct / 100) * scoreCircumference
  const scoreRingColor = overallScore >= 75 ? "#22c55e" : overallScore >= 60 ? "#eab308" : "#ef4444"

  return (
    <div className="page-wrap token-page dashboard-shell">
      <section className="token-summary fade-in fade-in-2">
        <div className="token-summary-left">
          <div className="token-path">
            <Link to="/" className="token-breadcrumb">Dashboard</Link>
            <span className="token-separator">/</span>
            <span>{displayName}</span>
          </div>
          <h1>{displayName}</h1>
          <span className="token-subtitle">{displayTicker} · Utility coin intelligence</span>
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
              <span className="token-score-large">{overallScore}</span>
            </div>
            <div className="token-score-copy">
              <span className="token-score-rating">{SCORE_LETTER(overallScore)} Rating</span>
              <span className="token-score-caption">Overall CCS Score</span>
            </div>
          </div>
        </div>
      </section>

      <section className="coin-kpi-row fade-in fade-in-2">
        <div className="kpi-card">
          <span className="kpi-label">CCS Score</span>
          <span className="kpi-value">{overallScore}<small>/100</small></span>
          <span className="kpi-meta">Grade {SCORE_LETTER(overallScore)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Automated Signal</span>
          <span className="kpi-value">{automatedTotal}<small>/75</small></span>
          <span className="kpi-meta">System-generated score</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Manual Validation</span>
          <span className="kpi-value">{manualTotal != null ? `${manualTotal}/25` : "In Progress"}</span>
          <span className="kpi-meta">Human validation</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Risk Level</span>
          <span className={`kpi-value risk-${riskLevel.toLowerCase()}`}>{riskLevel}</span>
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
                  <circle key={index} cx={point.x} cy={point.y} r={dotRadius} fill="rgba(255,255,255,0.95)">
                    <title>{point.date}: {point.score}</title>
                  </circle>
                ))}
              </svg>
            </div>
            <div className="trend-meta">
              <span>Latest score: {overallScore}</span>
              <span>{historyRaw.length > 0 ? `${earliestDate} → ${latestDate}` : "First cycle — history builds over time"}</span>
              <span>All-time high: {maxTrend}</span>
            </div>
          </section>

          <div className="split-cards">
            <MarketData data={marketData} loading={marketLoading} />
            <RecentNews data={news} loading={newsLoading} />
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
              <div className="dev-row"><span>Commits This Period</span><strong className="metric-state">Data Pending <span>Source integration in progress</span></strong></div>
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
