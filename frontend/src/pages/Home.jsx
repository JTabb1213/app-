import { useState } from "react"
import { useNavigate } from "react-router-dom"
import "./Home.css"

function Home() {
    const [coin, setCoin] = useState("")
    const [error, setError] = useState("")
    const navigate = useNavigate()

    const handleSubmit = (e) => {
        e.preventDefault()
        setError("")

        if (!coin.trim()) {
            setError("Please enter a coin name")
            return
        }

        navigate(`/coin/${coin.toLowerCase().trim()}`)
    }

    return (
        <div className="home-page">
            <div className="search-section">
                <h1 className="home-title">Crypto Rating</h1>
                <p className="home-subtitle">Search for any cryptocurrency to see its safety rating and tokenomics</p>

                <form className="search-form" onSubmit={handleSubmit}>
                    <input
                        className="search-input"
                        type="text"
                        placeholder="bitcoin, ethereum, cardano..."
                        value={coin}
                        onChange={(e) => {
                            setCoin(e.target.value)
                            setError("")
                        }}
                        autoFocus
                    />
                    <button className="search-button" type="submit" disabled={!coin.trim()}>
                        🔍 Search
                    </button>
                </form>

                {error && <p className="error-message">{error}</p>}
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