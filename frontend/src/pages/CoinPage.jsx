import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getCoinStatic, getTokenomics } from "../services/api";
import Tokenomics from "../components/Tokenomics";
import Score from "../components/Score";
import "./CoinPage.css"

function CoinPage() {
    const { coinId } = useParams();
    const navigate = useNavigate();

    const [staticData, setStaticData] = useState(null);
    const [tokenomics, setTokenomics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        const fetchAll = async () => {
            try {
                // Fetch DB static data and tokenomics (which may be cached)
                const [dbData, tokenData] = await Promise.all([
                    getCoinStatic(coinId),
                    getTokenomics(coinId),
                ]);

                setStaticData(dbData);
                setTokenomics(tokenData);
            } catch (err) {
                console.error("Fetch error:", err);
                setError(err.message || "Failed to load coin data. Please check the coin name and try again.");
            } finally {
                setLoading(false);
            }
        };

        if (coinId) {
            fetchAll();
        }
    }, [coinId]);

    if (loading) {
        return (
            <div className="page-container loading">
                <div className="spinner"></div>
                <p>Loading coin data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page-container error">
                <h2>⚠️ Error Loading Coin</h2>
                <p className="error-message">{error}</p>
                <button onClick={() => navigate("/")} className="back-btn">
                    ← Back to Search
                </button>
            </div>
        );
    }

    if (!tokenomics && !staticData) {
        return (
            <div className="page-container">
                <p>No coin data available</p>
                <button onClick={() => navigate("/")} className="back-btn">
                    ← Back to Search
                </button>
            </div>
        );
    }

    // Derive display values
    const coinName = tokenomics?.name || staticData?.name || coinId;
    const coinSymbol = tokenomics?.symbol || staticData?.symbol || "";

    return (
        <div className="page-container">
            <button onClick={() => navigate("/")} className="back-btn small">
                ← Back
            </button>

            <div className="coin-header-section">
                {staticData?.image_url && (
                    <img
                        src={staticData.image_url}
                        alt={coinName}
                        className="coin-logo"
                    />
                )}
                <h1>{coinName} <span className="symbol">({coinSymbol.toUpperCase()})</span></h1>
            </div>

            {/* Description from DB (user-editable later) */}
            <div className="description-section">
                <h3>Description</h3>
                <p className="description-text">
                    {staticData?.description || "No description available yet."}
                </p>
            </div>

            {/* Static info from DB */}
            {staticData && (
                <section className="static-section">
                    <h2>Coin Details</h2>
                    <div className="static-grid">
                        <div className="static-item"><span className="label">ATH</span><span className="val">${staticData.ath?.toLocaleString() ?? "N/A"}</span></div>
                        <div className="static-item"><span className="label">ATH Date</span><span className="val">{staticData.ath_date ? new Date(staticData.ath_date).toLocaleDateString() : "N/A"}</span></div>
                        <div className="static-item"><span className="label">ATL</span><span className="val">${staticData.atl?.toLocaleString() ?? "N/A"}</span></div>
                        <div className="static-item"><span className="label">ATL Date</span><span className="val">{staticData.atl_date ? new Date(staticData.atl_date).toLocaleDateString() : "N/A"}</span></div>
                        <div className="static-item"><span className="label">Circulating Supply</span><span className="val">{staticData.circulating_supply?.toLocaleString() ?? "N/A"}</span></div>
                        <div className="static-item"><span className="label">Total Supply</span><span className="val">{staticData.total_supply?.toLocaleString() ?? "N/A"}</span></div>
                        <div className="static-item"><span className="label">Max Supply</span><span className="val">{staticData.max_supply ? staticData.max_supply.toLocaleString() : "Unlimited"}</span></div>
                    </div>
                </section>
            )}

            {/* Rating / review info from DB */}
            {staticData && (
                <section className="review-section">
                    <h2>Community Rating</h2>
                    <p className="review-score">
                        {staticData.rating_score != null
                            ? `${staticData.rating_score} / 10`
                            : "No rating available yet."}
                    </p>
                    <p className="review-notes">{staticData.rating_notes || "No review notes available yet."}</p>
                    <p className="review-count">
                        {staticData.review_count != null
                            ? `${staticData.review_count} review(s)`
                            : "No reviews yet."}
                    </p>
                </section>
            )}

            {/* Existing tokenomics & score components */}
            <Tokenomics data={tokenomics} />
            <Score coinId={coinId} />
        </div>
    );
}

export default CoinPage;
