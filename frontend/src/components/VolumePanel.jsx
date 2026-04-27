import { useState, useEffect, useCallback } from "react"
import { getVolume } from "../services/api"
import "./VolumePanel.css"

const WINDOWS = ["5m", "30m", "4h", "24h"]

const WINDOW_LABELS = {
    "5m": "5 min",
    "30m": "30 min",
    "4h": "4 hour",
    "24h": "24 hour",
}

/**
 * VolumePanel — displays real-time buy/sell pressure for a coin.
 *
 * Fetches from GET /api/volume/<coin_id>?window=<window> and shows:
 *   • Buy volume bar vs. sell volume bar
 *   • Total volume in USD
 *   • Buy % vs Sell % breakdown
 *   • Window selector (5m, 30m, 4h, 24h)
 *
 * Auto-refreshes every 15s so the numbers stay current.
 */
function VolumePanel({ coinId }) {
    const [window, setWindow] = useState("5m")
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const formatVolume = (n) => {
        if (n == null) return "N/A"
        if (n >= 1e9) return (n / 1e9).toFixed(2) + "B"
        if (n >= 1e6) return (n / 1e6).toFixed(2) + "M"
        if (n >= 1e3) return (n / 1e3).toFixed(1) + "K"
        return n.toFixed(4)
    }

    const fetchVolume = useCallback(async () => {
        if (!coinId) return
        try {
            const result = await getVolume(coinId, window)
            setData(result)
            setError(null)
        } catch (err) {
            setError(err.message || "Failed to load volume data")
            setData(null)
        } finally {
            setLoading(false)
        }
    }, [coinId, window])

    // Fetch on mount and whenever coin/window changes
    useEffect(() => {
        setLoading(true)
        setData(null)
        fetchVolume()
    }, [fetchVolume])

    // Auto-refresh every 15 seconds
    useEffect(() => {
        const id = setInterval(fetchVolume, 15_000)
        return () => clearInterval(id)
    }, [fetchVolume])

    const sellPct = data ? (100 - data.buy_pct).toFixed(1) : 50

    return (
        <div className="volume-panel">
            {/* Window selector */}
            <div className="volume-window-row">
                {WINDOWS.map((w) => (
                    <button
                        key={w}
                        className={`window-btn ${window === w ? "active" : ""}`}
                        onClick={() => setWindow(w)}
                    >
                        {w}
                    </button>
                ))}
                <span className="volume-refresh-hint">auto-refresh 15s</span>
            </div>

            {loading && !data && (
                <div className="volume-loading">
                    <div className="spinner small"></div>
                    <p>Loading volume data…</p>
                </div>
            )}

            {error && !data && (
                <div className="volume-error">
                    <span className="volume-error-icon">⚠️</span>
                    <p>{error}</p>
                    <p className="volume-error-hint">
                        Volume data requires the realtime trade collectors and volume aggregator to be running.
                    </p>
                </div>
            )}

            {data && (
                <div className="volume-content">
                    {/* Exchange count indicator */}
                    <div className="volume-exchange-count">
                        <span className="exchange-label">Exchanges tracked</span>
                        <span className="exchange-badge">{data.exchange_count}</span>
                    </div>

                    {/* Total */}
                    <div className="volume-total-row">
                        <span className="volume-total-label">Total ({WINDOW_LABELS[window]})</span>
                        <span className="volume-total-value">{formatVolume(data.total_volume_usd)} <span className="volume-unit">coins</span></span>
                    </div>

                    {/* Buy/Sell bar */}
                    <div className="volume-bar-container">
                        <div
                            className="volume-bar-fill buy"
                            style={{ width: `${data.buy_pct}%` }}
                        />
                        <div
                            className="volume-bar-fill sell"
                            style={{ width: `${sellPct}%` }}
                        />
                    </div>

                    {/* Buy / Sell breakdown */}
                    <div className="volume-breakdown">
                        <div className="volume-side buy-side">
                            <span className="side-label">🟢 Buy</span>
                            <span className="side-value">{formatVolume(data.buy_volume_usd)}</span>
                            <span className="side-pct">{data.buy_pct}%</span>
                        </div>
                        <div className="volume-divider" />
                        <div className="volume-side sell-side">
                            <span className="side-label">🔴 Sell</span>
                            <span className="side-value">{formatVolume(data.sell_volume_usd)}</span>
                            <span className="side-pct">{sellPct}%</span>
                        </div>
                    </div>

                    {/* Pressure indicator */}
                    <div className={`pressure-badge ${data.buy_pct >= 55 ? "bullish" : data.buy_pct <= 45 ? "bearish" : "neutral"}`}>
                        {data.buy_pct >= 55
                            ? "📈 Bullish Pressure"
                            : data.buy_pct <= 45
                                ? "📉 Bearish Pressure"
                                : "⚖️ Neutral"}
                    </div>
                </div>
            )}
        </div>
    )
}

export default VolumePanel
