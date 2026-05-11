import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getCoinStatic, getTokenomics } from "../services/api";
import { useRealtimePrice } from "../hooks/useRealtimePrice";
import Tokenomics from "../components/Tokenomics";
import Score from "../components/Score";
import LiveDataPanel from "../components/LiveDataPanel";
import "./CoinPage.css"

function CoinPage() {
    const { coinId } = useParams();
    const navigate = useNavigate();

    const [staticData, setStaticData] = useState(null);
    const [tokenomics, setTokenomics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Real-time price data via WebSocket (independent of REST fetches)
    const { priceData: realtimeData, connectionState: wsState, error: wsError } = useRealtimePrice(coinId);

    useEffect(() => {
        setLoading(true);
        setError(null);

        const fetchAll = async () => {
            // Fetch each source independently — a REST failure (e.g. CORS in dev)
            // must never block the page from rendering or the WS section from showing.
            const [dbData, tokenData] = await Promise.allSettled([
                getCoinStatic(coinId),
                getTokenomics(coinId),
            ]);

            const resolvedStatic = dbData.status === "fulfilled" ? dbData.value : null;
            const resolvedTokens = tokenData.status === "fulfilled" ? tokenData.value : null;

            setStaticData(resolvedStatic);
            setTokenomics(resolvedTokens);

            // Only show a blocking error if BOTH sources failed AND there's no name to show
            if (!resolvedStatic && !resolvedTokens) {
                const firstErr = dbData.reason || tokenData.reason;
                setError(firstErr?.message || "Could not load coin data from the API.");
            }

            setLoading(false);
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

    // Derive display values — fall back to coinId if API data unavailable
    const coinName = tokenomics?.name || staticData?.name || coinId;
    const coinSymbol = tokenomics?.symbol || staticData?.symbol || "";

    return (
        <div className="page-container">
            <button onClick={() => navigate("/")} className="back-btn small">
                ← Back
            </button>

            {/* Non-blocking API error banner — page still renders with WS data */}
            {error && (
                <div className="api-error-banner">
                    ⚠️ API unavailable: {error}. Live exchange data below is still active.
                </div>
            )}

            <div className="coin-header-section">
                {staticData?.image_url && (
                    <img
                        src={staticData.image_url}
                        alt={coinName}
                        className="coin-logo"
                    />
                )}
                <h1>{coinName} <span className="symbol">({coinSymbol.toUpperCase()})</span></h1>
                {realtimeData?.avg_price != null && (
                    <span className="current-price live-price">
                        ${realtimeData.avg_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        <span className="live-tag">LIVE</span>
                    </span>
                )}
            </div>

            {/* Live price + volume switcher */}
            <LiveDataPanel
                coinId={coinId}
                priceData={realtimeData}
                connectionState={wsState}
                wsError={wsError}
            />

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
