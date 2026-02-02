import { useEffect, useState } from "react";
import { getScore } from "../services/api";
import "./Score.css"

function Score({ coinId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Reset state when coin changes
        setData(null);
        setError(null);
        setLoading(true);

        const fetchScore = async () => {
            try {
                const result = await getScore(coinId);
                setData(result);
                setError(null);
            } catch (err) {
                console.error("Score fetch error:", err);
                setError(err.message || "Failed to load score. Please try again.");
                setData(null);
            } finally {
                setLoading(false);
            }
        };

        if (coinId) {
            fetchScore();
        }
    }, [coinId]);

    // Loading state
    if (loading) {
        return (
            <section className="score-section loading">
                <div className="spinner"></div>
                <p>Loading rating...</p>
            </section>
        );
    }

    // Error state
    if (error) {
        return (
            <section className="score-section error">
                <p className="error-message">⚠️ {error}</p>
                <p className="error-hint">Make sure the coin name is correct and try again.</p>
            </section>
        );
    }

    // Empty state
    if (!data) {
        return (
            <section className="score-section empty">
                <p>No rating data available</p>
            </section>
        );
    }

    const { score, breakdown } = data;
    const hasGitHub = breakdown.github_activity?.metrics && Object.keys(breakdown.github_activity.metrics).length > 0;

    // Score badge color based on rating
    const getScoreColor = (s) => {
        if (s >= 80) return "excellent";
        if (s >= 60) return "good";
        if (s >= 40) return "fair";
        return "poor";
    };

    return (
        <section className="score-section">
            <div className={`score-card ${getScoreColor(score)}`}>
                <h2>Overall Rating</h2>
                <div className="score-badge">{score.toFixed(1)}</div>
                <p className="score-label">/100</p>
            </div>

            <div className="breakdown">
                <h3>Score Breakdown</h3>
                <div className="factors-grid">
                    <div className="factor">
                        <div className="factor-header">
                            <span className="factor-name">Market Cap</span>
                            <span className="factor-weight">{(breakdown.market_cap.weight * 100).toFixed(0)}%</span>
                        </div>
                        <div className="score-bar">
                            <div
                                className="score-fill"
                                style={{ width: `${breakdown.market_cap.score}%` }}
                            ></div>
                        </div>
                        <p className="factor-score">{breakdown.market_cap.score}/100</p>
                        <p className="factor-detail">
                            ${breakdown.market_cap.value >= 1e9
                                ? (breakdown.market_cap.value / 1e9).toFixed(2) + "B"
                                : (breakdown.market_cap.value / 1e6).toFixed(2) + "M"}
                        </p>
                    </div>

                    <div className="factor">
                        <div className="factor-header">
                            <span className="factor-name">24h Volume</span>
                            <span className="factor-weight">{(breakdown.volume_24h.weight * 100).toFixed(0)}%</span>
                        </div>
                        <div className="score-bar">
                            <div
                                className="score-fill"
                                style={{ width: `${breakdown.volume_24h.score}%` }}
                            ></div>
                        </div>
                        <p className="factor-score">{breakdown.volume_24h.score}/100</p>
                        <p className="factor-detail">
                            ${breakdown.volume_24h.value >= 1e9
                                ? (breakdown.volume_24h.value / 1e9).toFixed(2) + "B"
                                : (breakdown.volume_24h.value / 1e6).toFixed(2) + "M"}
                        </p>
                    </div>

                    <div className="factor">
                        <div className="factor-header">
                            <span className="factor-name">Holder Diversity</span>
                            <span className="factor-weight">{(breakdown.holder_diversity.weight * 100).toFixed(0)}%</span>
                        </div>
                        <div className="score-bar">
                            <div
                                className="score-fill"
                                style={{ width: `${breakdown.holder_diversity.score}%` }}
                            ></div>
                        </div>
                        <p className="factor-score">{breakdown.holder_diversity.score}/100</p>
                        <p className="factor-detail">
                            {(breakdown.holder_diversity.value * 100).toFixed(1)}% concentration risk
                        </p>
                    </div>

                    <div className="factor">
                        <div className="factor-header">
                            <span className="factor-name">GitHub Activity</span>
                            <span className="factor-weight">{(breakdown.github_activity.weight * 100).toFixed(0)}%</span>
                        </div>
                        <div className="score-bar">
                            <div
                                className="score-fill"
                                style={{ width: `${breakdown.github_activity.score}%` }}
                            ></div>
                        </div>
                        <p className="factor-score">{breakdown.github_activity.score}/100</p>
                        {hasGitHub ? (
                            <details className="github-details">
                                <summary>View details</summary>
                                <div className="github-repo-link">
                                    <a href={breakdown.github_activity.metrics.url} target="_blank" rel="noopener noreferrer" className="repo-link">
                                        → Visit Repository
                                    </a>
                                </div>
                                <ul className="github-metrics">
                                    <li>
                                        <span className="metric-label">Stars:</span>
                                        <span>{breakdown.github_activity.metrics.stars?.toLocaleString() || "N/A"}</span>
                                    </li>
                                    <li>
                                        <span className="metric-label">Commits:</span>
                                        <span>{breakdown.github_activity.metrics.commits_year || "N/A"}</span>
                                    </li>
                                    <li>
                                        <span className="metric-label">Contributors:</span>
                                        <span>{breakdown.github_activity.metrics.contributors?.toLocaleString() || "N/A"}</span>
                                    </li>
                                    <li>
                                        <span className="metric-label">Forks:</span>
                                        <span>{breakdown.github_activity.metrics.forks?.toLocaleString() || "N/A"}</span>
                                    </li>
                                    <li>
                                        <span className="metric-label">License:</span>
                                        <span>{breakdown.github_activity.metrics.license || "Not specified"}</span>
                                    </li>
                                </ul>
                            </details>
                        ) : (
                            <p className="factor-detail text-muted">Repository not in database</p>
                        )}
                    </div>
                </div>
            </div>
        </section>
    );
}

export default Score;
