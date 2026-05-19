import "./Score.css"

// TODO: Remove this fake data and replace with a real API call when backend is ready.
// e.g. const data = await fetch(`/api/score/${coinId}`).then(r => r.json())
const FAKE_SCORE = {
    overall_score: 82.5,
    automated_score: 57.5,
    manual_validation: 25,
    risk_level: "Low",
    security_transparency: {
        score: 30,
        max: 35,
        metrics: { top_10_pct: 18.4, largest_wallet_pct: 4.1, holder_count: 45000 }
    },
    tokenomics_utility: {
        score: 18,
        max: 20,
        metrics: { has_max_supply: true, inflation_potential_pct: 0.2 }
    },
    community_dev_activity: {
        score: 13,
        max: 15,
        metrics: {
            delta_commits: 142,
            contributor_count: 980,
            github_url: "https://github.com/bitcoin/bitcoin",
            stars: 75000
        }
    },
    public_discourse: {
        score: 4.2,
        max: 5,
        metrics: { sentiment_score: 2.1, interest_score: 2.1 }
    }
}

function CategoryBar({ label, score, max, children }) {
    const pct = Math.round((score / max) * 100)
    const color = pct >= 80 ? "excellent" : pct >= 60 ? "good" : pct >= 40 ? "fair" : "poor"

    return (
        <div className="vertical-factor">
            <div className="factor-header">
                <span className="factor-name">{label}</span>
                <span className="factor-weight">{score}/{max}</span>
            </div>
            <div className="score-bar-vertical">
                <div className={`score-fill-vertical ${color}`} style={{ height: `${pct}%` }} />
            </div>
            <p className="factor-score">{pct}%</p>
            {children}
        </div>
    )
}

function Score() {
    const d = FAKE_SCORE

    const getRiskColor = (r) => ({
        Low: "excellent",
        Moderate: "good",
        High: "poor",
    }[r] || "fair")

    return (
        <section className="score-section">
            <div className={`score-card ${getRiskColor(d.risk_level)}`}>
                <h2>Overall Rating</h2>
                <div className="score-badge">{d.overall_score.toFixed(1)}</div>
                <p className="score-label">/100</p>
                <p className="score-sublabel">
                    {d.automated_score} automated + {d.manual_validation} analyst review
                </p>
                <span className={`risk-badge ${getRiskColor(d.risk_level)}`}>{d.risk_level} Risk</span>
            </div>

            <div className="breakdown">
                <h3>Score Breakdown</h3>
                <div className="factors-vertical-container">

                    <CategoryBar
                        label="Security &amp; Transparency"
                        score={d.security_transparency.score}
                        max={d.security_transparency.max}
                    >
                        {d.security_transparency.metrics.diversity_method === "hashrate" ? (
                            <>
                                <p className="factor-detail">Nakamoto coefficient: {d.security_transparency.metrics.nakamoto_coefficient}</p>
                                <p className="factor-detail">Largest pool: {d.security_transparency.metrics.largest_pool_pct}%</p>
                                <p className="factor-detail">Pool count: {d.security_transparency.metrics.pool_count}</p>
                            </>
                        ) : d.security_transparency.metrics.diversity_method === "validator" ? (
                            <>
                                <p className="factor-detail">Nakamoto coefficient: {d.security_transparency.metrics.nakamoto_coefficient}</p>
                                <p className="factor-detail">Largest entity: {d.security_transparency.metrics.largest_entity_pct}%</p>
                            </>
                        ) : d.security_transparency.metrics.diversity_method === "vesting" ? (
                            <>
                                <p className="factor-detail">Insider allocation: {d.security_transparency.metrics.insider_pct}%</p>
                                <p className="factor-detail">Circulating ratio: {d.security_transparency.metrics.circulating_ratio}</p>
                            </>
                        ) : (
                            <>
                                <p className="factor-detail">Top 10 wallets: {d.security_transparency.metrics.top_10_pct}%</p>
                                <p className="factor-detail">Largest wallet: {d.security_transparency.metrics.largest_wallet_pct}%</p>
                                <p className="factor-detail">Holders: {d.security_transparency.metrics.holder_count?.toLocaleString()}</p>
                            </>
                        )}
                    </CategoryBar>

                    <CategoryBar
                        label="Tokenomics &amp; Utility"
                        score={d.tokenomics_utility.score}
                        max={d.tokenomics_utility.max}
                    >
                        <p className="factor-detail">
                            Capped supply: {d.tokenomics_utility.metrics.has_max_supply ? "Yes" : "No"}
                        </p>
                        <p className="factor-detail">
                            Inflation potential: {d.tokenomics_utility.metrics.inflation_potential_pct?.toFixed(1) ?? "N/A"}%
                        </p>
                    </CategoryBar>

                    <CategoryBar
                        label="Community &amp; Dev Activity"
                        score={d.community_dev_activity.score}
                        max={d.community_dev_activity.max}
                    >
                        <details className="github-details">
                            <summary>View details</summary>
                            {d.community_dev_activity.metrics.github_url && (
                                <div className="github-repo-link">
                                    <a
                                        href={d.community_dev_activity.metrics.github_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="repo-link"
                                    >
                                        → Visit Repository
                                    </a>
                                </div>
                            )}
                            <ul className="github-metrics">
                                <li>
                                    <span className="metric-label">Commits this period:</span>
                                    <span>{d.community_dev_activity.metrics.delta_commits}</span>
                                </li>
                                <li>
                                    <span className="metric-label">Contributors:</span>
                                    <span>{d.community_dev_activity.metrics.contributor_count?.toLocaleString()}</span>
                                </li>
                                <li>
                                    <span className="metric-label">Stars:</span>
                                    <span>{d.community_dev_activity.metrics.stars?.toLocaleString()}</span>
                                </li>
                            </ul>
                        </details>
                    </CategoryBar>

                    <CategoryBar
                        label="Public Discourse"
                        score={d.public_discourse.score}
                        max={d.public_discourse.max}
                    >
                        <p className="factor-detail">
                            Reddit sentiment: {d.public_discourse.metrics.reddit_compound?.toFixed(2) ?? "N/A"}
                        </p>
                        <p className="factor-detail">
                            Search interest: {d.public_discourse.metrics.search_interest ?? "N/A"}/100
                        </p>
                    </CategoryBar>

                </div>
            </div>
        </section>
    )
}

export default Score
