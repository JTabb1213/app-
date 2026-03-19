"use client";

import { useState } from "react";

export default function CachePage() {
    /* ---- Refresh Popular ---- */
    const [popularResult, setPopularResult] = useState(null);
    const [popularLoading, setPopularLoading] = useState(false);

    /* ---- Refresh Single Coin ---- */
    const [singleCoinId, setSingleCoinId] = useState("");
    const [singleResult, setSingleResult] = useState(null);
    const [singleLoading, setSingleLoading] = useState(false);

    /* ---- Lookup Alias ---- */
    const [lookupTerm, setLookupTerm] = useState("");
    const [lookupResult, setLookupResult] = useState(null);

    /* ================================================================
       Handlers
       ================================================================ */

    async function refreshPopular() {
        setPopularLoading(true);
        setPopularResult(null);
        try {
            const res = await fetch("/api/admin/cache/refresh-popular", {
                method: "POST",
            });
            setPopularResult(await res.json());
        } catch (err) {
            setPopularResult({ error: err.message });
        } finally {
            setPopularLoading(false);
        }
    }

    async function refreshSingleCoin() {
        if (!singleCoinId.trim()) return;
        setSingleLoading(true);
        setSingleResult(null);
        try {
            const res = await fetch("/api/admin/cache/refresh-coin", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ coin_id: singleCoinId.trim() }),
            });
            setSingleResult(await res.json());
        } catch (err) {
            setSingleResult({ error: err.message });
        } finally {
            setSingleLoading(false);
        }
    }

    async function lookupAlias() {
        if (!lookupTerm.trim()) return;
        try {
            const res = await fetch(
                `/api/admin/cache/alias/${lookupTerm.trim().toLowerCase()}`
            );
            setLookupResult(await res.json());
        } catch {
            setLookupResult({ error: "Lookup failed" });
        }
    }

    /* ================================================================
       Render
       ================================================================ */

    return (
        <div>
            <h1 className="page-title">Cache Management</h1>

            {/* ---- Top section: refresh actions ---- */}
            <div className="cache-grid">
                {/* Refresh Popular */}
                <div className="cache-card">
                    <h2 className="cache-card-title">🔥 Refresh Popular Coins</h2>
                    <p className="cache-card-desc">
                        Fetches fresh tokenomics for the top 20 popular coins and pushes
                        them into the Redis cache.
                    </p>
                    <button
                        onClick={refreshPopular}
                        className="btn btn-primary"
                        disabled={popularLoading}
                    >
                        {popularLoading ? "Refreshing…" : "Refresh Top 20"}
                    </button>
                    {popularResult && (
                        <div
                            className={`result-box ${popularResult.error ? "error" : "success"
                                }`}
                        >
                            {popularResult.error
                                ? `Error: ${popularResult.error}`
                                : `✓ Updated ${popularResult.succeeded}/${popularResult.total} coins`}
                        </div>
                    )}
                </div>

                {/* Refresh Single Coin */}
                <div className="cache-card">
                    <h2 className="cache-card-title">🪙 Refresh Single Coin</h2>
                    <p className="cache-card-desc">
                        Update the cache for one specific coin.
                    </p>
                    <div className="inline-form">
                        <input
                            type="text"
                            placeholder="e.g. bitcoin"
                            value={singleCoinId}
                            onChange={(e) => setSingleCoinId(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && refreshSingleCoin()}
                        />
                        <button
                            onClick={refreshSingleCoin}
                            className="btn btn-primary"
                            disabled={singleLoading}
                        >
                            {singleLoading ? "…" : "Refresh"}
                        </button>
                    </div>
                    {singleResult && (
                        <div
                            className={`result-box ${singleResult.errors?.length ? "warning" : "success"
                                }`}
                        >
                            {singleResult.tokenomics_updated
                                ? `✓ Cache updated for ${singleResult.coin_id}`
                                : `✗ Failed: ${singleResult.errors?.join(", ") || "unknown"}`}
                        </div>
                    )}
                </div>
            </div>

            {/* ---- Alias Management section ---- */}
            <h2 className="section-title" style={{ marginTop: "2rem" }}>
                Alias Lookup
            </h2>
            <p className="cache-card-desc" style={{ marginBottom: "1rem" }}>
                Aliases are now stored in{" "}
                <code>data/coin_aliases.json</code> (not Redis).
                To update aliases, edit the JSON file or run{" "}
                <code>python tools/populate_aliases/main.py</code>.
            </p>

            <div className="cache-grid">
                {/* Lookup Alias */}
                <div className="cache-card">
                    <h2 className="cache-card-title">🔍 Lookup Alias</h2>
                    <p className="cache-card-desc">
                        Check what a search term currently resolves to from the
                        alias map.
                    </p>
                    <div className="inline-form">
                        <input
                            type="text"
                            placeholder="e.g. btc, xbt, ethereum"
                            value={lookupTerm}
                            onChange={(e) => setLookupTerm(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && lookupAlias()}
                        />
                        <button onClick={lookupAlias} className="btn btn-accent">
                            Lookup
                        </button>
                    </div>

                    {lookupResult && (
                        <div className="alias-result">
                            {lookupResult.resolved_to ? (
                                <p>
                                    <span className="badge">{lookupResult.term}</span>
                                    <span className="arrow"> → </span>
                                    <span className="badge badge-accent">
                                        {lookupResult.resolved_to}
                                    </span>
                                </p>
                            ) : (
                                <p className="text-muted">
                                    No alias found for &apos;{lookupResult.term}&apos;
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
