import { useState } from "react"
import { useNavigate } from "react-router-dom"
import CoinSearch from "../components/CoinSearch"
import "./Home.css"

function Home() {
    const navigate = useNavigate()

    return (
        <div className="home-page">
            <div className="search-section">
                <h1 className="home-title">Crypto Rating</h1>
                <p className="home-subtitle">Search for any cryptocurrency to see its safety rating and tokenomics</p>

                <CoinSearch />
            </div>

            <div className="info-section">
                <h3 className="info-title">How it Works</h3>
                <ul className="info-list">
                    <li className="info-item"><span className="info-icon">📊</span> <strong>Market Cap</strong> - Project size and maturity (25%)</li>
                    <li className="info-item"><span className="info-icon">💰</span> <strong>24h Volume</strong> - Liquidity and trading activity (15%)</li>
                    <li className="info-item"><span className="info-icon">👥</span> <strong>Holder Diversity</strong> - Token distribution risk (25%)</li>
                    <li className="info-item"><span className="info-icon">⚙️</span> <strong>GitHub Activity</strong> - Development momentum (35%)</li>
                </ul>
            </div>
        </div>
    )
}

export default Home