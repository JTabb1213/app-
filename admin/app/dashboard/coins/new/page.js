"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const SECTIONS = [
    {
        title: "Basic Info",
        fields: [
            { key: "id", label: "Coin ID (e.g. bitcoin)", type: "text" },
            { key: "name", label: "Name", type: "text" },
            { key: "symbol", label: "Symbol", type: "text" },
            { key: "image_url", label: "Image URL", type: "text" },
            { key: "github_url", label: "GitHub URL", type: "text" },
        ],
    },
    {
        title: "Market Data",
        fields: [
            { key: "market_cap_rank", label: "Market Cap Rank", type: "number" },
            { key: "circulating_supply", label: "Circulating Supply", type: "number" },
            { key: "total_supply", label: "Total Supply", type: "number" },
            { key: "max_supply", label: "Max Supply", type: "number" },
            { key: "fully_diluted_valuation", label: "Fully Diluted Valuation", type: "number" },
        ],
    },
    {
        title: "Price Records",
        fields: [
            { key: "ath", label: "All-Time High (USD)", type: "number" },
            { key: "ath_date", label: "ATH Date", type: "text" },
            { key: "atl", label: "All-Time Low (USD)", type: "number" },
            { key: "atl_date", label: "ATL Date", type: "text" },
        ],
    },
    {
        title: "Editorial",
        fields: [
            { key: "description", label: "Description", type: "textarea" },
            { key: "rating_score", label: "Rating Score (0–10)", type: "number" },
            { key: "rating_notes", label: "Rating Notes", type: "textarea" },
            { key: "review_count", label: "Review Count", type: "number" },
            { key: "is_featured", label: "Featured", type: "checkbox" },
        ],
    },
];

const NUMERIC_KEYS = [
    "market_cap_rank", "circulating_supply", "total_supply", "max_supply",
    "fully_diluted_valuation", "ath", "atl", "rating_score", "review_count",
];

export default function NewCoinPage() {
    const router = useRouter();
    const [form, setForm] = useState({});
    const [creating, setCreating] = useState(false);
    const [autofilling, setAutofilling] = useState(false);
    const [message, setMessage] = useState(null);

    function handleChange(key, value) {
        setForm((prev) => ({ ...prev, [key]: value }));
    }

    /* ---- Auto-fill from CoinGecko (does NOT save yet) ---- */
    async function handleAutofill() {
        const coinId = form.id?.trim();
        if (!coinId) {
            setMessage({ type: "error", text: "Enter a Coin ID first." });
            return;
        }
        setAutofilling(true);
        setMessage(null);

        try {
            const res = await fetch(`/api/admin/autofill/${coinId}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Auto-fill failed");
            setForm(data);
            setMessage({
                type: "success",
                text: `Auto-filled data for "${data.name || coinId}".`,
            });
        } catch (err) {
            setMessage({ type: "error", text: err.message });
        } finally {
            setAutofilling(false);
        }
    }

    /* ---- Create coin ---- */
    async function handleCreate(e) {
        e.preventDefault();
        setCreating(true);
        setMessage(null);

        const cleaned = { ...form };
        for (const key of NUMERIC_KEYS) {
            if (cleaned[key] === "" || cleaned[key] === undefined)
                cleaned[key] = null;
            else if (cleaned[key] !== null) cleaned[key] = Number(cleaned[key]);
        }

        try {
            const res = await fetch("/api/admin/coins", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(cleaned),
            });
            const data = await res.json();

            // ---- Duplicate detected (409) ----
            if (res.status === 409) {
                setMessage({
                    type: "warning",
                    text: data.error,
                    existingCoin: data.existing_coin,
                });
                return;
            }

            if (!res.ok) throw new Error(data.error || "Create failed");

            setMessage({ type: "success", text: "Coin created successfully!" });
            setTimeout(
                () => router.push(`/dashboard/coins/${data.coin.id}`),
                800
            );
        } catch (err) {
            setMessage({ type: "error", text: err.message });
        } finally {
            setCreating(false);
        }
    }

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Create New Coin</h1>
                <button
                    onClick={() => router.push("/dashboard/coins")}
                    className="btn btn-secondary"
                >
                    ← Back to Coins
                </button>
            </div>

            {/* ---- Alert / duplicate warning ---- */}
            {message && (
                <div className={`alert alert-${message.type}`}>
                    {message.text}
                    {message.existingCoin && (
                        <>
                            {" "}
                            <Link href={`/dashboard/coins/${message.existingCoin}`}>
                                Edit existing coin →
                            </Link>
                        </>
                    )}
                </div>
            )}

            {/* ---- Auto-fill button ---- */}
            <div
                className="form-section"
                style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem" }}
            >
                <div className="form-group" style={{ flex: 1 }}>
                    <label htmlFor="autofill-id">
                        Coin ID (enter, then auto-fill from CoinGecko)
                    </label>
                    <input
                        id="autofill-id"
                        type="text"
                        placeholder="e.g. bitcoin, cardano, solana"
                        value={form.id ?? ""}
                        onChange={(e) => handleChange("id", e.target.value)}
                    />
                </div>
                <button
                    type="button"
                    onClick={handleAutofill}
                    className="btn btn-accent"
                    disabled={autofilling}
                    style={{ marginBottom: "0.15rem" }}
                >
                    {autofilling ? "Fetching…" : "⬇ Auto-fill from CoinGecko"}
                </button>
            </div>

            {/* ---- Form ---- */}
            <form onSubmit={handleCreate}>
                {SECTIONS.map((section) => (
                    <div key={section.title} className="form-section">
                        <h2 className="section-title">{section.title}</h2>
                        <div className="form-grid">
                            {section.fields.map((field) => (
                                <div
                                    key={field.key}
                                    className={`form-group ${field.type === "textarea" ? "full-width" : ""
                                        }`}
                                >
                                    <label htmlFor={`new-${field.key}`}>{field.label}</label>

                                    {field.type === "textarea" ? (
                                        <textarea
                                            id={`new-${field.key}`}
                                            value={form[field.key] ?? ""}
                                            onChange={(e) => handleChange(field.key, e.target.value)}
                                            rows={field.key === "description" ? 6 : 3}
                                        />
                                    ) : field.type === "checkbox" ? (
                                        <input
                                            id={`new-${field.key}`}
                                            type="checkbox"
                                            checked={!!form[field.key]}
                                            onChange={(e) =>
                                                handleChange(field.key, e.target.checked)
                                            }
                                        />
                                    ) : (
                                        <input
                                            id={`new-${field.key}`}
                                            type={field.type}
                                            step={field.type === "number" ? "any" : undefined}
                                            value={form[field.key] ?? ""}
                                            onChange={(e) => handleChange(field.key, e.target.value)}
                                        />
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}

                <div className="form-actions">
                    <button
                        type="submit"
                        className="btn btn-success"
                        disabled={creating}
                    >
                        {creating ? "Creating…" : "✅ Create Coin"}
                    </button>
                </div>
            </form>

            {form.image_url && (
                <div className="preview-section">
                    <h3>Image Preview</h3>
                    <img
                        src={form.image_url}
                        alt={form.name}
                        className="image-preview"
                    />
                </div>
            )}
        </div>
    );
}
