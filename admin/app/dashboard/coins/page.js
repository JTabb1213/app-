"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function CoinsPage() {
    const [coins, setCoins] = useState([]);
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        fetch("/api/admin/coins")
            .then((r) => r.json())
            .then((data) => setCoins(data.coins || []))
            .catch(() => { })
            .finally(() => setLoading(false));
    }, []);

    const filtered = coins.filter(
        (c) =>
            c.name?.toLowerCase().includes(search.toLowerCase()) ||
            c.symbol?.toLowerCase().includes(search.toLowerCase()) ||
            c.id?.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Manage Coins</h1>
                <Link href="/dashboard/coins/new" className="btn btn-primary">
                    + Create New Coin
                </Link>
            </div>

            <div className="search-bar">
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search by name, symbol, or ID…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {loading ? (
                <div className="loading-container small">
                    <div className="spinner" />
                </div>
            ) : (
                <div className="table-container">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th></th>
                                <th>Name</th>
                                <th>Symbol</th>
                                <th>ID</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="no-results">
                                        {coins.length === 0
                                            ? "No coins in database. Populate some first!"
                                            : "No coins match your search."}
                                    </td>
                                </tr>
                            ) : (
                                filtered.map((coin) => (
                                    <tr key={coin.id}>
                                        <td>{coin.market_cap_rank || "—"}</td>
                                        <td>
                                            {coin.image_url ? (
                                                <img
                                                    src={coin.image_url}
                                                    alt=""
                                                    className="coin-avatar"
                                                />
                                            ) : (
                                                <div className="coin-avatar-placeholder">?</div>
                                            )}
                                        </td>
                                        <td className="bold">{coin.name}</td>
                                        <td className="uppercase">{coin.symbol}</td>
                                        <td className="muted">{coin.id}</td>
                                        <td>
                                            <button
                                                onClick={() =>
                                                    router.push(`/dashboard/coins/${coin.id}`)
                                                }
                                                className="btn btn-sm btn-accent"
                                            >
                                                Edit
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
