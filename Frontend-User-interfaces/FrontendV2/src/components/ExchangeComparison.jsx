import "./ExchangeComparison.css"

/**
 * Displays a live comparison of prices across exchanges for a coin.
 *
 * Shows:
 *   • The cheapest exchange to buy from  (lowest price)
 *   • Average price across all exchanges
 *   • The most expensive exchange        (highest price)
 *   • Price spread percentage
 *
 * Handles three states gracefully:
 *   1. Connecting / waiting for data  → spinner
 *   2. Error                          → detailed error message
 *   3. Live data                      → the three comparison cards
 */
function ExchangeComparison({ priceData, connectionState, error }) {
    const formatPrice = (num) => {
        if (num == null) return "N/A"
        if (num >= 1)
            return (
                "$" +
                num.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })
            )
        return (
            "$" +
            num.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 8,
            })
        )
    }

    const formatExchange = (name) => {
        if (!name) return "N/A"
        return name.charAt(0).toUpperCase() + name.slice(1)
    }

    // ── Error state ─────────────────────────────────────────────
    if (error) {
        return (
            <section className="exchange-section">
                <h2>Realtime Price</h2>
                <div className="exchange-error">
                    <div className="exchange-error-header">
                        <span className="exchange-error-icon">⚠️</span>
                        <span className="exchange-error-title">
                            WebSocket Connection Error
                        </span>
                    </div>
                    <pre className="exchange-error-detail">{error}</pre>
                    <p className="exchange-error-hint">
                        Real-time exchange comparison requires a live WebSocket connection.
                        The rest of the page data is unaffected.
                    </p>
                </div>
            </section>
        )
    }

    // ── Connecting / waiting for first data ─────────────────────
    if (connectionState === "connecting" || !priceData) {
        return (
            <section className="exchange-section">
                <h2>Realtime Price</h2>
                <div className="exchange-loading">
                    <div className="spinner small"></div>
                    <p>
                        {connectionState === "connecting"
                            ? "Connecting to real-time feed..."
                            : "Waiting for price data..."}
                    </p>
                </div>
            </section>
        )
    }

    // ── Live data ───────────────────────────────────────────────
    const {
        avg_price,
        highest_exchange,
        highest_price,
        lowest_exchange,
        lowest_price,
        exchange_count,
        timestamp,
    } = priceData

    const spread =
        highest_price && lowest_price
            ? (((highest_price - lowest_price) / lowest_price) * 100).toFixed(3)
            : null

    const lastUpdated = timestamp
        ? new Date(timestamp * 1000).toLocaleTimeString()
        : "N/A"

    return (
        <section className="exchange-section">
            <h2>Realtime Price</h2>

            <div className="exchange-status">
                <span className="status-dot connected"></span>
                <span>
                    Live • {exchange_count} exchange
                    {exchange_count !== 1 ? "s" : ""} • Updated {lastUpdated}
                </span>
            </div>

            <div className="exchange-grid">
                {/* Cheapest */}
                <div className="exchange-card cheapest">
                    <div className="card-badge cheapest-badge">💰 Cheapest</div>
                    <h3>{formatExchange(lowest_exchange)}</h3>
                    <p className="exchange-price">{formatPrice(lowest_price)}</p>
                    <p className="card-hint">Best price to buy</p>
                </div>

                {/* Average */}
                <div className="exchange-card average">
                    <div className="card-badge average-badge">📊 Average</div>
                    <h3>
                        Across {exchange_count} Exchange
                        {exchange_count !== 1 ? "s" : ""}
                    </h3>
                    <p className="exchange-price">{formatPrice(avg_price)}</p>
                    {spread && <p className="card-hint">Spread: {spread}%</p>}
                </div>

                {/* Most expensive */}
                <div className="exchange-card expensive">
                    <div className="card-badge expensive-badge">🔺 Most Expensive</div>
                    <h3>{formatExchange(highest_exchange)}</h3>
                    <p className="exchange-price">{formatPrice(highest_price)}</p>
                    <p className="card-hint">Highest price</p>
                </div>
            </div>
        </section>
    )
}

export default ExchangeComparison
