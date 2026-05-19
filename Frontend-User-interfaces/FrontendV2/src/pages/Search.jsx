import { useState, useEffect } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { loadSearchIndex, searchCoins } from "../services/coinSearch"
import "./Search.css"

function Search() {
  const [searchParams] = useSearchParams()
  const initialQ = searchParams.get("q") || ""
  const [query, setQuery] = useState(initialQ)
  const [index, setIndex] = useState([])

  useEffect(() => {
    loadSearchIndex().then(setIndex)
  }, [])

  const results = query.trim()
    ? searchCoins(query, index)
    : index.slice(0, 50)

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

      <p className="results-count fade-in fade-in-2">
        {results.length} token{results.length !== 1 ? "s" : ""} found
      </p>

      <div className="search-results fade-in fade-in-3">
        {results.map((coin) => (
          <Link
            to={`/token/${coin.id}`}
            className="result-card"
            key={coin.id}
          >
            <div className="result-left">
              <div className="result-icon" />
              <div className="result-info">
                <span className="result-name">{coin.name}</span>
                <span className="result-ticker">{coin.symbol}</span>
              </div>
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
