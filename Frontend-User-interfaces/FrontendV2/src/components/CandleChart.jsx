import { useEffect, useRef, useState } from "react"
import { createChart, CandlestickSeries, LineSeries } from "lightweight-charts"
import { getCandles } from "../services/api"
import "./CandleChart.css"

// Each tab defines:
//   resolution → which DB table to query (1h / 1d / 1w / 1month)
//   limit      → how many candles back to fetch
//   disabled   → greyed out until live data is wired up
const RESOLUTIONS = [
    { id: "live", label: "1H", resolution: "1h", limit: 24, disabled: true },
    { id: "1d", label: "1D", resolution: "1h", limit: 24, disabled: false },
    { id: "1w", label: "1W", resolution: "1h", limit: 168, disabled: false },
    { id: "1month", label: "1M", resolution: "1d", limit: 30, disabled: false },
    { id: "3month", label: "3M", resolution: "1d", limit: 90, disabled: false },
    { id: "1year", label: "1Y", resolution: "1d", limit: 365, disabled: false },
    { id: "5year", label: "5Y", resolution: "1w", limit: 260, disabled: false },
    { id: "max", label: "Max", resolution: "1month", limit: 600, disabled: false },
]

export default function CandleChart({ coinId }) {
    const containerRef = useRef(null)
    const chartRef = useRef(null)
    const seriesRef = useRef(null)
    const lastDataRef = useRef([])   // cache last fetched rows to avoid re-fetch on mode switch
    const tooltipRef = useRef(null)  // floating price tooltip element

    const [activeTab, setActiveTab] = useState("1d")
    const [chartMode, setChartMode] = useState("candle")  // "candle" | "line"
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // ── Create chart once on mount ──────────────────────────────────────────
    useEffect(() => {
        if (!containerRef.current) return

        const chart = createChart(containerRef.current, {
            layout: {
                background: { color: "#0f1117" },
                textColor: "#9ca3af",
                attributionLogo: false,   // removes the TradingView watermark logo
            },
            grid: {
                vertLines: { color: "#1f2937" },
                horzLines: { color: "#1f2937" },
            },
            crosshair: { mode: 1 },
            rightPriceScale: { borderColor: "#374151" },
            timeScale: {
                borderColor: "#374151",
                timeVisible: true,
                secondsVisible: false,
            },
            width: containerRef.current.clientWidth,
            height: 320,
        })

        chartRef.current = chart

        // ── Crosshair price tooltip ────────────────────────────────────────
        chart.subscribeCrosshairMove(param => {
            const tooltip = tooltipRef.current
            if (!tooltip) return

            if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
                tooltip.style.display = "none"
                return
            }

            // Get the price value at the crosshair position
            const series = seriesRef.current
            if (!series) return
            const data = param.seriesData.get(series)
            if (!data) { tooltip.style.display = "none"; return }

            const price = data.close ?? data.value ?? null
            if (price == null) { tooltip.style.display = "none"; return }

            // Format price — use commas, up to 8 decimal places but trim trailing zeros
            const formatted = price >= 1
                ? price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : price.toPrecision(6)

            tooltip.textContent = `$${formatted}`
            tooltip.style.display = "block"

            // Position: above the crosshair point, clamped to container bounds
            const containerWidth = containerRef.current?.clientWidth ?? 400
            const ttWidth = tooltip.offsetWidth || 80
            let left = param.point.x - ttWidth / 2
            left = Math.max(4, Math.min(left, containerWidth - ttWidth - 4))
            tooltip.style.left = `${left}px`
            tooltip.style.top = `${Math.max(4, param.point.y - 36)}px`
        })

        const ro = new ResizeObserver(() => {
            if (containerRef.current)
                chart.applyOptions({ width: containerRef.current.clientWidth })
        })
        ro.observe(containerRef.current)

        return () => {
            ro.disconnect()
            chart.remove()
        }
    }, [])

    // ── Rebuild series whenever chart mode changes ──────────────────────────
    useEffect(() => {
        const chart = chartRef.current
        if (!chart) return

        // Remove old series
        if (seriesRef.current) {
            chart.removeSeries(seriesRef.current)
            seriesRef.current = null
        }

        // Add new series of the right type
        if (chartMode === "candle") {
            seriesRef.current = chart.addSeries(CandlestickSeries, {
                upColor: "#22c55e",
                downColor: "#ef4444",
                borderVisible: false,
                wickUpColor: "#22c55e",
                wickDownColor: "#ef4444",
            })
        } else {
            seriesRef.current = chart.addSeries(LineSeries, {
                color: "#3b82f6",
                lineWidth: 2,
            })
        }

        // Re-apply cached data so we don't re-fetch just for a mode switch
        if (lastDataRef.current.length > 0) {
            const rows = chartMode === "candle"
                ? lastDataRef.current
                : lastDataRef.current.map(c => ({ time: c.time, value: c.close }))
            seriesRef.current.setData(rows)
            chart.timeScale().fitContent()
        }
    }, [chartMode])

    // ── Fetch data whenever coinId or activeTab changes ────────────────────
    useEffect(() => {
        if (!seriesRef.current) return

        const tab = RESOLUTIONS.find(r => r.id === activeTab)
        if (!tab || tab.disabled) return

        let cancelled = false
        setLoading(true)
        setError(null)

        getCandles(coinId, tab.resolution, tab.limit)
            .then(data => {
                if (cancelled) return

                if (!data.candles || data.candles.length === 0) {
                    // No data — show a flat line at 0 instead of an overlay
                    const now = Math.floor(Date.now() / 1000)
                    const flatLine = [
                        { time: now - tab.limit * 86400, value: 0 },
                        { time: now, value: 0 },
                    ]
                    lastDataRef.current = []
                    // Switch to line mode for the flat line (candlestick needs OHLC)
                    const series = seriesRef.current
                    if (series) {
                        series.setData(
                            chartMode === "candle"
                                ? []   // empty candlestick = blank chart
                                : flatLine
                        )
                        chartRef.current.timeScale().fitContent()
                    }
                } else {
                    // Store raw OHLCV rows for mode-switching
                    lastDataRef.current = data.candles.map(c => ({
                        time: c.time,
                        open: c.open,
                        high: c.high,
                        low: c.low,
                        close: c.close,
                    }))

                    const rows = chartMode === "candle"
                        ? lastDataRef.current
                        : lastDataRef.current.map(c => ({ time: c.time, value: c.close }))

                    seriesRef.current.setData(rows)
                    chartRef.current.timeScale().fitContent()
                }
            })
            .catch(err => {
                if (cancelled) return
                setError("Failed to load chart data")
            })
            .finally(() => { if (!cancelled) setLoading(false) })

        return () => { cancelled = true }
    }, [coinId, activeTab])

    return (
        <div className="candle-chart-wrapper">
            <div className="candle-chart-header">
                <span className="candle-chart-title">Price Chart</span>

                {/* Mode toggle */}
                <div className="candle-mode-switcher">
                    <button
                        className={`candle-mode-btn ${chartMode === "candle" ? "active" : ""}`}
                        onClick={() => setChartMode("candle")}
                        title="Candlestick"
                    >🕯</button>
                    <button
                        className={`candle-mode-btn ${chartMode === "line" ? "active" : ""}`}
                        onClick={() => setChartMode("line")}
                        title="Line"
                    >📈</button>
                </div>

                {/* Resolution switcher */}
                <div className="candle-res-switcher">
                    {RESOLUTIONS.map(r => (
                        <button
                            key={r.id}
                            className={`candle-res-btn ${activeTab === r.id ? "active" : ""} ${r.disabled ? "disabled" : ""}`}
                            onClick={() => !r.disabled && setActiveTab(r.id)}
                            title={r.disabled ? "Live data coming soon" : undefined}
                        >
                            {r.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="candle-chart-body">
                {loading && <div className="candle-overlay">Loading chart…</div>}
                {!loading && error && (
                    <div className="candle-overlay candle-error">{error}</div>
                )}
                <div ref={containerRef} className="candle-chart-canvas" />
                <div ref={tooltipRef} className="candle-price-tooltip" style={{ display: "none" }} />
            </div>
        </div>
    )
}
