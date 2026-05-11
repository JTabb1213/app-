import "./Tokenomics.css"

function Tokenomics({ data }) {
    if (!data) return null;

    const formatNumber = (num) => {
        if (!num) return "N/A";
        if (num >= 1e9) return (num / 1e9).toFixed(2) + "B";
        if (num >= 1e6) return (num / 1e6).toFixed(2) + "M";
        return num.toLocaleString();
    };

    const formatPrice = (num) => {
        if (num == null) return "N/A";
        if (num >= 1) return "$" + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        // For very small prices show up to 8 decimal places
        return "$" + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 });
    };

    const change24h = data.price_change_percentage_24h;
    const changePositive = change24h != null && change24h >= 0;

    return (
        <section className="tokenomics-section">
            <h2>Tokenomics</h2>

            <div className="tokenomics-grid">
                {data.current_price != null && (
                    <div className="tokenomics-card price-card">
                        <h3>Live Price</h3>
                        <p className="value">{formatPrice(data.current_price)}</p>
                        {change24h != null && (
                            <p className={`price-change ${changePositive ? "positive" : "negative"}`}>
                                {changePositive ? "▲" : "▼"} {Math.abs(change24h).toFixed(2)}% (24h)
                            </p>
                        )}
                    </div>
                )}

                <div className="tokenomics-card">
                    <h3>Market Cap</h3>
                    <p className="value">${data.market_cap?.toLocaleString() || "N/A"}</p>
                </div>

                {data.total_volume && (
                    <div className="tokenomics-card">
                        <h3>24h Volume</h3>
                        <p className="value">${data.total_volume?.toLocaleString() || "N/A"}</p>
                    </div>
                )}

                <div className="tokenomics-card">
                    <h3>Circulating Supply</h3>
                    <p className="value">{formatNumber(data.circulating_supply)}</p>
                </div>

                <div className="tokenomics-card">
                    <h3>Total Supply</h3>
                    <p className="value">{formatNumber(data.total_supply)}</p>
                </div>

                <div className="tokenomics-card">
                    <h3>Max Supply</h3>
                    <p className="value">{data.max_supply ? formatNumber(data.max_supply) : "Unlimited"}</p>
                </div>
            </div>
        </section>
    );
}

export default Tokenomics;
