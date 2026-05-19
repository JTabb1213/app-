import "./RecentNews.css"

function fmt_date(pubDateStr) {
    if (!pubDateStr) return null
    try {
        const d = new Date(pubDateStr)
        const now = new Date()
        const diffMs = now - d
        const diffH = Math.floor(diffMs / 3_600_000)
        const diffD = Math.floor(diffMs / 86_400_000)
        if (diffH < 1) return "Just now"
        if (diffH < 24) return `${diffH}h ago`
        if (diffD < 7) return `${diffD}d ago`
        return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
    } catch {
        return pubDateStr
    }
}

export default function RecentNews({ data, loading }) {
    const articles = data?.articles ?? []

    return (
        <section className="panel small-panel news-panel">
            <div className="panel-header">
                <h3>Recent News</h3>

            </div>

            {loading && (
                <div className="news-list">
                    {[...Array(4)].map((_, i) => (
                        <div className="news-item news-skeleton" key={i}>
                            <div className="news-skeleton-line long" />
                            <div className="news-skeleton-line short" />
                        </div>
                    ))}
                </div>
            )}

            {!loading && articles.length === 0 && (
                <div className="news-unavailable">
                    <span>News unavailable</span>
                    <small>Could not fetch recent articles</small>
                </div>
            )}

            {!loading && articles.length > 0 && (
                <div className="news-list">
                    {articles.map((article, i) => (
                        <a
                            className="news-item"
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            key={i}
                        >
                            <div className="news-meta">
                                <span className="news-source">{article.source}</span>
                                <span className="news-time">{fmt_date(article.published_at)}</span>
                            </div>
                            <div className="news-title">{article.title}</div>
                        </a>
                    ))}
                </div>
            )}
        </section>
    )
}
