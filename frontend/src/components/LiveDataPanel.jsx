import { useState } from "react"
import ExchangeComparison from "./ExchangeComparison"
import VolumePanel from "./VolumePanel"
import "./LiveDataPanel.css"

const TABS = [
    { id: "price", label: "📡 Live Price" },
    { id: "volume", label: "📊 Volume" },
]

/**
 * LiveDataPanel — a single card that lets the user switch between:
 *   • Live Price  — real-time exchange comparison via WebSocket
 *   • Volume      — buy/sell pressure from the REST volume API
 *
 * Both views share the same box so they don't eat up extra screen space.
 */
function LiveDataPanel({ coinId, priceData, connectionState, wsError }) {
    const [activeTab, setActiveTab] = useState("price")

    return (
        <div className="live-data-panel">
            {/* Tab switcher */}
            <div className="live-data-tabs">
                {TABS.map((tab) => (
                    <button
                        key={tab.id}
                        className={`live-tab-btn ${activeTab === tab.id ? "active" : ""}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        {tab.label}
                        {tab.id === "price" && connectionState === "connected" && (
                            <span className="tab-live-dot" />
                        )}
                    </button>
                ))}
            </div>

            {/* Panel content */}
            <div className="live-data-body">
                {activeTab === "price" && (
                    <ExchangeComparison
                        priceData={priceData}
                        connectionState={connectionState}
                        error={wsError}
                        embedded
                    />
                )}
                {activeTab === "volume" && (
                    <VolumePanel coinId={coinId} />
                )}
            </div>
        </div>
    )
}

export default LiveDataPanel
