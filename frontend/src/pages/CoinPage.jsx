import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getTokenomics } from "../services/api";
import Tokenomics from "../components/tokenomics"; // Ensure correct import with capital T
import Score from "../components/Score";
import "./CoinPage.css"

function CoinPage() {
    const { coinId } = useParams();
    const navigate = useNavigate();

    const [tokenomics, setTokenomics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        const fetchTokenomics = async () => {
            try {
                const data = await getTokenomics(coinId);
                setTokenomics(data);
            } catch (err) {
                console.error("Tokenomics fetch error:", err);
                setError(err.message || "Failed to load coin data. Please check the coin name and try again.");
            } finally {
                setLoading(false);
            }
        };

        if (coinId) {
            fetchTokenomics();
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

    if (!tokenomics) {
        return (
            <div className="page-container">
                <p>No coin data available</p>
                <button onClick={() => navigate("/")} className="back-btn">
                    ← Back to Search
                </button>
            </div>
        );
    }

    return (
        <div className="page-container">
            <button onClick={() => navigate("/")} className="back-btn small">
                ← Back
            </button>

            <h1>{tokenomics.name} <span className="symbol">({tokenomics.symbol.toUpperCase()})</span></h1>

            <Tokenomics data={tokenomics} />
            <Score coinId={coinId} />
        </div>
    );
}

export default CoinPage;
