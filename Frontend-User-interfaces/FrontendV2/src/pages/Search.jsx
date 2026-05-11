import { useState, useMemo } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { MOCK_TOKENS, getScoreColor } from "../services/mockData"
import "./Search.css"

function Search() {
  const [searchParams] = useSearchParams()
  const initialQ = searchParams.get("q") || ""
  const [query, setQuery] = useState(initialQ)
  const [scoreRange, setScoreRange] = useState("all")
  const [reviewFilter, setReviewFilter] = useState("all")

  const results = useMemo(() => {
    let filtered = MOCK_TOKENS

    if (query.trim()) {
      const q = query.toLowerCase()
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.ticker.toLowerCase().includes(q)
      )
    }

    if (scoreRange !== "all") {
      const [min, max] = scoreRange.split("-").map(Number)
      filtered = filtered.filter((t) => t.overallScore >= min && t.overallScore <= max)
    }

    if (reviewFilter !== "all") {
      filtered = filtered.filter((t) => t.reviewStatus === reviewFilter)
    }

    return filtered
  }, [query, scoreRange, reviewFilter])

  return (
    <div className="page-wrap search-page">
      <section className="search-hero fade-in fade-in-1">
        <h1>Token Search</h1>
        <input
          className="search-bar"
          type="text"
          placeholder="Search by name or ticker..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
      </section>

      <div className="search-filters fade-in fade-in-2">
        <div className="filter-group">
          <label className="filter-label">Score Range</label>
          <select
            className="filter-select"
            value={scoreRange}
            onChange={(e) => setScoreRange(e.target.value)}
          >
            <option value="all">All Scores</option>
            <option value="75-100">75 – 100</option>
            <option value="50-74">50 – 74</option>
            <option value="25-49">25 – 49</option>
            <option value="0-24">0 – 24</option>
          </select>
        </div>
        <div className="filter-group">
          <label className="filter-label">Review Status</label>
          <select
            className="filter-select"
            value={reviewFilter}
            onChange={(e) => setReviewFilter(e.target.value)}
          >
            <option value="all">All</option>
            <option value="complete">Reviewed</option>
            <option value="pending">Pending Review</option>
          </select>
        </div>
      </div>

      <p className="results-count fade-in fade-in-3">
        {results.length} token{results.length !== 1 ? "s" : ""} found
      </p>

      <div className="search-results fade-in fade-in-3">
        {results.map((token) => (
          <Link
            to={`/token/${token.id}`}
            className="result-card"
            key={token.id}
          >
            <div className="result-left">
              <div className="result-icon" />
              <div className="result-info">
                <span className="result-name">{token.name}</span>
                <span className="result-ticker">{token.ticker}</span>
              </div>
            </div>
            <div className="result-right">
              <span className={`result-score ${getScoreColor(token.overallScore)}`}>
                {token.overallScore} <span className="score-of">/ 100</span>
              </span>
              <span className={`status-pill ${token.reviewStatus}`}>
                {token.reviewStatus === "complete" ? "Reviewed" : "Pending Review"}
              </span>
            </div>
          </Link>
        ))}

        {results.length === 0 && (
          <div className="no-results">
            <p>No tokens match your search criteria.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Search
