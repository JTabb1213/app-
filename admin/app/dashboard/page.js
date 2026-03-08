"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function DashboardPage() {
    const [stats, setStats] = useState(null);
    const [coinCount, setCoinCount] = useState(0);

    useEffect(() => {
        fetch("/api/admin/cache/stats")
            .then((r) => r.json())
            .then(setStats)
            .catch(() => { });

        fetch("/api/admin/coins")
            .then((r) => r.json())
            .then((data) => setCoinCount(data.coins?.length || 0))
            .catch(() => { });
    }, []);

    return (
        <div>
            <h1 className="page-title">Dashboard</h1>

            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon">🪙</div>
                    <div className="stat-value">{coinCount}</div>
                    <div className="stat-label">Coins in Database</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon">🔑</div>
                    <div className="stat-value">{stats?.total_keys ?? "—"}</div>
                    <div className="stat-label">Redis Keys</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon">💾</div>
                    <div className="stat-value">{stats?.used_memory_human ?? "—"}</div>
                    <div className="stat-label">Cache Memory</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon">{stats?.connected ? "🟢" : "🔴"}</div>
                    <div className="stat-value">
                        {stats?.connected ? "Online" : "Offline"}
                    </div>
                    <div className="stat-label">Redis Status</div>
                </div>
            </div>

            <h2 className="section-title">Quick Actions</h2>
            <div className="action-grid">
                <Link href="/dashboard/coins" className="action-card">
                    <span className="action-icon">📝</span>
                    <span className="action-label">Manage Coins</span>
                    <span className="action-desc">
                        Edit coin data in the SQL database
                    </span>
                </Link>
                <Link href="/dashboard/coins/new" className="action-card">
                    <span className="action-icon">➕</span>
                    <span className="action-label">Create New Coin</span>
                    <span className="action-desc">
                        Add a new cryptocurrency entry
                    </span>
                </Link>
                <Link href="/dashboard/cache" className="action-card">
                    <span className="action-icon">🔄</span>
                    <span className="action-label">Cache Management</span>
                    <span className="action-desc">
                        Refresh cache and manage aliases
                    </span>
                </Link>
            </div>
        </div>
    );
}
