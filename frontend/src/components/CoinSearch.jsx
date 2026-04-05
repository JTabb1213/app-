import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { loadSearchIndex, searchCoins } from "../services/coinSearch"
import "./CoinSearch.css"

/**
 * Autocomplete coin search.
 *
 * Loads the search index on mount, then as the user types,
 * filters the list down to matching coins (by id, symbol, name,
 * or any alias). Clicking a result navigates to /coin/:id.
 *
 * Keyboard navigation: ↑/↓ to move, Enter to select, Esc to close.
 */
function CoinSearch() {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState([])
    const [index, setIndex] = useState([])
    const [isOpen, setIsOpen] = useState(false)
    const [activeIdx, setActiveIdx] = useState(-1)
    const [loading, setLoading] = useState(true)

    const navigate = useNavigate()
    const inputRef = useRef(null)
    const listRef = useRef(null)

    // ── Load search index on mount ──────────────────────────────
    useEffect(() => {
        loadSearchIndex().then((data) => {
            setIndex(data)
            setLoading(false)
        })
    }, [])

    // ── Filter results as user types ────────────────────────────
    useEffect(() => {
        if (!query.trim()) {
            setResults([])
            setIsOpen(false)
            return
        }
        const matches = searchCoins(query, index)
        setResults(matches)
        setIsOpen(matches.length > 0)
        setActiveIdx(-1)
    }, [query, index])

    // ── Close dropdown on outside click ─────────────────────────
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (
                listRef.current &&
                !listRef.current.contains(e.target) &&
                inputRef.current &&
                !inputRef.current.contains(e.target)
            ) {
                setIsOpen(false)
            }
        }
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    // ── Select a coin ───────────────────────────────────────────
    const selectCoin = useCallback(
        (coin) => {
            setQuery("")
            setIsOpen(false)
            navigate(`/coin/${coin.id}`)
        },
        [navigate]
    )

    // ── Keyboard handler ────────────────────────────────────────
    const handleKeyDown = (e) => {
        if (!isOpen) return

        if (e.key === "ArrowDown") {
            e.preventDefault()
            setActiveIdx((prev) => Math.min(prev + 1, results.length - 1))
        } else if (e.key === "ArrowUp") {
            e.preventDefault()
            setActiveIdx((prev) => Math.max(prev - 1, 0))
        } else if (e.key === "Enter") {
            e.preventDefault()
            if (activeIdx >= 0 && results[activeIdx]) {
                selectCoin(results[activeIdx])
            }
        } else if (e.key === "Escape") {
            setIsOpen(false)
        }
    }

    // ── Handle form submit (fallback: navigate with raw query) ──
    const handleSubmit = (e) => {
        e.preventDefault()
        if (activeIdx >= 0 && results[activeIdx]) {
            selectCoin(results[activeIdx])
        } else if (results.length === 1) {
            selectCoin(results[0])
        } else if (query.trim()) {
            // No match in index — navigate anyway (future: API lookup)
            navigate(`/coin/${query.toLowerCase().trim()}`)
        }
    }

    // ── Scroll active item into view ────────────────────────────
    useEffect(() => {
        if (activeIdx >= 0 && listRef.current) {
            const items = listRef.current.querySelectorAll(".search-result-item")
            if (items[activeIdx]) {
                items[activeIdx].scrollIntoView({ block: "nearest" })
            }
        }
    }, [activeIdx])

    return (
        <div className="coin-search-wrapper">
            <form className="search-form" onSubmit={handleSubmit}>
                <div className="search-input-wrapper">
                    <input
                        ref={inputRef}
                        className="search-input"
                        type="text"
                        placeholder={loading ? "Loading coins..." : "Search by name, symbol, or ticker..."}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => query.trim() && results.length > 0 && setIsOpen(true)}
                        onKeyDown={handleKeyDown}
                        autoFocus
                        autoComplete="off"
                        spellCheck="false"
                    />

                    {/* Dropdown results */}
                    {isOpen && (
                        <ul className="search-results-dropdown" ref={listRef}>
                            {results.map((coin, i) => (
                                <li
                                    key={coin.id}
                                    className={`search-result-item ${i === activeIdx ? "active" : ""}`}
                                    onMouseDown={(e) => {
                                        e.preventDefault() // keep focus on input
                                        selectCoin(coin)
                                    }}
                                    onMouseEnter={() => setActiveIdx(i)}
                                >
                                    <span className="result-symbol">{coin.symbol}</span>
                                    <span className="result-name">{coin.name}</span>
                                    <span className="result-id">{coin.id}</span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <button
                    className="search-button"
                    type="submit"
                    disabled={!query.trim()}
                >
                    🔍 Search
                </button>
            </form>

            {/* Hint when query matches nothing in the index */}
            {query.trim() && results.length === 0 && !loading && (
                <p className="search-no-match">
                    No known coin matches "<strong>{query}</strong>".
                    Press Enter to search anyway.
                </p>
            )}
        </div>
    )
}

export default CoinSearch
