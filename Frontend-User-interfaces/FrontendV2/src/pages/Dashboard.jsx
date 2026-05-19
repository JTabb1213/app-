import "./Dashboard.css"

function Dashboard() {
  return (
    <div className="page-wrap dashboard-page">
      <header className="dash-header fade-in fade-in-1">
        <h1>Dashboard</h1>
        <p className="dash-subtitle">Track your watched tokens and monitor score changes.</p>
      </header>

      <section className="watchlist-section fade-in fade-in-2">
        <h2>Watched Tokens</h2>
        <p className="dash-empty">Watchlist coming soon — use Search to explore coins.</p>
      </section>
    </div>
  )
}

export default Dashboard
