"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

export default function DashboardLayout({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        fetch("/api/auth/session")
            .then((res) => {
                if (!res.ok) throw new Error();
                return res.json();
            })
            .then((data) => setUser(data))
            .catch(() => router.push("/login"))
            .finally(() => setLoading(false));
    }, [router]);

    async function handleLogout() {
        await fetch("/api/auth/logout", { method: "POST" });
        router.push("/login");
    }

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner" />
                <p>Checking session…</p>
            </div>
        );
    }

    if (!user) return null;

    const links = [
        { href: "/dashboard", label: "Dashboard" },
        { href: "/dashboard/coins", label: "Coins" },
        { href: "/dashboard/cache", label: "Cache" },
    ];

    return (
        <div className="app-wrapper">
            <nav className="nav">
                <div className="nav-inner">
                    <div className="nav-brand">⚡ Crypto Admin</div>
                    <div className="nav-links">
                        {links.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={`nav-link ${pathname === link.href ? "active" : ""}`}
                            >
                                {link.label}
                            </Link>
                        ))}
                    </div>
                    <div className="nav-right">
                        <span className="nav-user">👤 {user.username}</span>
                        <button onClick={handleLogout} className="btn btn-sm btn-secondary">
                            Logout
                        </button>
                    </div>
                </div>
            </nav>
            <main className="main-content">{children}</main>
        </div>
    );
}
