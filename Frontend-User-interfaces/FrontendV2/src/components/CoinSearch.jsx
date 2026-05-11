import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { loadSearchIndex, searchCoins } from "../services/coinSearch"
import "./CoinSearch.css"

/**
 * Autocomplete coin search for MockUserInterface.
 *
 * On match, navigates to /token/:coinId (the mock frontend's route).
 * Keyboard: ↑/↓ to move, Enter to select, Esc to close.
 */
function CoinSearch({ placeholder = "Search by name, symbol, or ticker..." }) {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState([])
    const [index, setIndex] = useState([])
    const [isOpen, setIsOpen] = useState(false)
    const [activeIdx, setActiveIdx] = useState(-1)
    const [loading, setLoading] = useState(true)

    const navigate = useNavigate()
    const inputRef = useRef(null)
    const listRef = useRef(null)

    useEffect(() => {
        loadSearchIndex().then((data) => {
            setIndex(data)
            setLoading(false)
        })
    }, [])

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

    const selectCoin = useCallback(
        (coin) => {
            setQuery("")
            setIsOpen(false)
            navigate(`/token/${coin.id}`)
        },
        [navigate]
    )

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
            if (activeIdx >= 0 && results[activeIdx]) selectCoin(results[activeIdx])
        } else if (e.key === "Escape") {
            setIsOpen(false)
        }
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        if (activeIdx >= 0 && results[activeIdx]) {
            selectCoin(results[activeIdx])
        } else if (results.length === 1) {
            selectCoin(results[0])
        } else if (query.trim()) {
            navigate(`/token/${query.toLowerCase().trim()}`)
        }
    }

    useEffect(() => {
        if (activeIdx >= 0 && listRef.current) {
            const items = listRef.current.querySelectorAll(".cs-result-item")
            if (items[activeIdx]) items[activeIdx].scrollIntoView({ block: "nearest" })
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
                        placeholder={loading ? "Loading coins..." : placeholder}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => query.trim() && results.length > 0 && setIsOpen(true)}
                        onKeyDown={handleKeyDown}
                        autoComplete="off"
                        spellCheck="false"
                    />

                    {isOpen && (
                        <ul className="cs-results-dropdown" ref={listRef}>
                            {results.map((coin, i) => (
                                <li
                                    key={coin.id}
                                    className={`cs-result-item ${i === activeIdx ? "active" : ""}`}
                                    onMouseDown={(e) => {
                                        e.preventDefault()
                                        selectCoin(coin)
                                    }}
                                    onMouseEnter={() => setActiveIdx(i)}
                                >
                                    <span className="cs-result-symbol">{coin.symbol}</span>
                                    <span className="cs-result-name">{coin.name}</span>
                                    <span className="cs-result-id">{coin.id}</span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <button className="search-button" type="submit" disabled={!query.trim()}>
                    🔍 Search
                </button>
            </form>

            {query.trim() && results.length === 0 && !loading && (
                <p className="cs-no-match">
                    No known coin matches "<strong>{query}</strong>".
                    Press Enter to search anyway.
                </p>
            )}
        </div>
    )
}

export default CoinSearch
