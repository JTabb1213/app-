import "./Tokenomics.css"

function Tokenomics({ data }) {
    if (!data) return null;

    const formatNumber = (num) => {
        if (!num) return "N/A";
        if (num >= 1e9) return (num / 1e9).toFixed(2) + "B";
        if (num >= 1e6) return (num / 1e6).toFixed(2) + "M";
        return num.toLocaleString();
    };

    return (
        <section className="tokenomics-section">
            <h2>Tokenomics</h2>

            <div className="tokenomics-grid">
                <div className="tokenomics-card">
                    <h3>Market Cap</h3>
                    <p className="value">${data.market_cap?.toLocaleString() || "N/A"}</p>
                </div>

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
