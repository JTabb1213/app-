import "./MarketData.css"

function fmt_currency(value) {
    if (value == null) return null
    if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
    return `$${value.toLocaleString()}`
}

function fmt_supply(value) {
    if (value == null) return null
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
    return value.toLocaleString()
}

function fmt_date(iso) {
    if (!iso) return null
    try {
        return new Date(iso).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        })
    } catch {
        return iso
    }
}

export default function MarketData({ data, loading }) {
    const PENDING = <strong className="metric-state">Data Pending <span>Source integration in progress</span></strong>
    const UNAVAIL = <strong className="metric-state">Unavailable <span>Could not fetch from CoinGecko</span></strong>

    const marketCap = data ? fmt_currency(data.market_cap_usd) : null
    const circulatingSupply = data ? fmt_supply(data.circulating_supply) : null
    const lastUpdated = data ? fmt_date(data.last_fetched_at) : null

    function Row({ label, value }) {
        let display
        if (loading) display = PENDING
        else if (!data) display = UNAVAIL
        else if (!value) display = UNAVAIL
        else display = <strong>{value}</strong>
        return (
            <div className="list-item">
                <span>{label}</span>
                {display}
            </div>
        )
    }

    return (
        <section className="panel small-panel">
            <div className="panel-header">
                <h3>Market Data</h3>

            </div>
            <div className="list-group">
                <Row label="Market Cap" value={marketCap} />
                <Row label="Circulating Supply" value={circulatingSupply} />
                <Row label="Last Updated" value={lastUpdated} />
            </div>
        </section>
    )
}
