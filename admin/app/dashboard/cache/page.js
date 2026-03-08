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

    /* ---- Rebuild Aliases ---- */
    const [aliasesResult, setAliasesResult] = useState(null);
    const [aliasesLoading, setAliasesLoading] = useState(false);

    /* ---- Lookup Alias ---- */
    const [lookupTerm, setLookupTerm] = useState("");
    const [lookupResult, setLookupResult] = useState(null);

    /* ---- Set Alias ---- */
    const [newAliasTerm, setNewAliasTerm] = useState("");
    const [newAliasTarget, setNewAliasTarget] = useState("");
    const [aliasMessage, setAliasMessage] = useState(null);

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

    async function refreshAllAliases() {
        setAliasesLoading(true);
        setAliasesResult(null);
        try {
            const res = await fetch("/api/admin/cache/refresh-aliases", {
                method: "POST",
            });
            setAliasesResult(await res.json());
        } catch (err) {
            setAliasesResult({ error: err.message });
        } finally {
            setAliasesLoading(false);
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

    async function deleteAlias() {
        if (!lookupResult?.term) return;
        try {
            await fetch(`/api/admin/cache/alias/${lookupResult.term}`, {
                method: "DELETE",
            });
            setLookupResult({ ...lookupResult, resolved_to: null, deleted: true });
        } catch {
            /* ignore */
        }
    }

    async function setAlias() {
        if (!newAliasTerm.trim() || !newAliasTarget.trim()) return;
        setAliasMessage(null);
        try {
            const res = await fetch("/api/admin/cache/alias", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    term: newAliasTerm.trim(),
                    target: newAliasTarget.trim(),
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            setAliasMessage({
                type: "success",
                text: `✓ '${data.term}' now maps to '${data.target}'`,
            });
            setNewAliasTerm("");
            setNewAliasTarget("");
        } catch (err) {
            setAliasMessage({ type: "error", text: err.message });
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

                {/* Rebuild All Aliases */}
                <div className="cache-card">
                    <h2 className="cache-card-title">🔗 Rebuild All Aliases</h2>
                    <p className="cache-card-desc">
                        Re-fetches the full CoinGecko coin list and rebuilds every alias
                        mapping. Top-market-cap coins get symbol priority (fixes btc →
                        batcat-type issues).
                    </p>
                    <button
                        onClick={refreshAllAliases}
                        className="btn btn-primary"
                        disabled={aliasesLoading}
                    >
                        {aliasesLoading ? "Rebuilding…" : "Rebuild Aliases"}
                    </button>
                    {aliasesResult && (
                        <div
                            className={`result-box ${aliasesResult.error ? "error" : "success"
                                }`}
                        >
                            {aliasesResult.error
                                ? `Error: ${aliasesResult.error}`
                                : `✓ Updated ${aliasesResult.aliases_updated} aliases from ${aliasesResult.coins_processed} coins`}
                        </div>
                    )}
                </div>
            </div>

            {/* ---- Alias Management section ---- */}
            <h2 className="section-title" style={{ marginTop: "2rem" }}>
                Alias Management
            </h2>

            <div className="cache-grid">
                {/* Lookup Alias */}
                <div className="cache-card">
                    <h2 className="cache-card-title">🔍 Lookup Alias</h2>
                    <p className="cache-card-desc">
                        Check what a search term currently resolves to, and optionally
                        delete it.
                    </p>
                    <div className="inline-form">
                        <input
                            type="text"
                            placeholder="e.g. btc, ada, ethereum"
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
                            {lookupResult.deleted ? (
                                <p className="text-success">
                                    ✓ Alias &apos;{lookupResult.term}&apos; has been deleted.
                                </p>
                            ) : lookupResult.resolved_to ? (
                                <>
                                    <p>
                                        <span className="badge">{lookupResult.term}</span>
                                        <span className="arrow"> → </span>
                                        <span className="badge badge-accent">
                                            {lookupResult.resolved_to}
                                        </span>
                                    </p>
                                    <button
                                        onClick={deleteAlias}
                                        className="btn btn-sm btn-danger"
                                        style={{ marginTop: "0.65rem" }}
                                    >
                                        🗑 Delete This Alias
                                    </button>
                                </>
                            ) : (
                                <p className="text-muted">
                                    No alias found for &apos;{lookupResult.term}&apos;
                                </p>
                            )}
                        </div>
                    )}
                </div>

                {/* Set / Overwrite Alias */}
                <div className="cache-card">
                    <h2 className="cache-card-title">✏️ Set Alias</h2>
                    <p className="cache-card-desc">
                        Create or overwrite an alias mapping. e.g.&nbsp;
                        <strong>btc → bitcoin</strong>
                    </p>
                    <div className="alias-form">
                        <div className="form-group">
                            <label>Search Term</label>
                            <input
                                type="text"
                                value={newAliasTerm}
                                onChange={(e) => setNewAliasTerm(e.target.value)}
                                placeholder="e.g. btc"
                            />
                        </div>
                        <div className="form-group">
                            <label>Target Coin ID</label>
                            <input
                                type="text"
                                value={newAliasTarget}
                                onChange={(e) => setNewAliasTarget(e.target.value)}
                                placeholder="e.g. bitcoin"
                            />
                        </div>
                        <button onClick={setAlias} className="btn btn-primary">
                            Set Alias
                        </button>
                    </div>
                    {aliasMessage && (
                        <div className={`result-box ${aliasMessage.type}`}>
                            {aliasMessage.text}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
