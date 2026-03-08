"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const SECTIONS = [
    {
        title: "Basic Info",
        fields: [
            { key: "id", label: "Coin ID", type: "text", readonly: true },
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

export default function EditCoinPage() {
    const { coinId } = useParams();
    const router = useRouter();
    const [form, setForm] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    useEffect(() => {
        fetch(`/api/admin/coins/${coinId}`)
            .then((r) => {
                if (!r.ok) throw new Error("Coin not found");
                return r.json();
            })
            .then((data) => setForm(data))
            .catch((err) => setMessage({ type: "error", text: err.message }))
            .finally(() => setLoading(false));
    }, [coinId]);

    function handleChange(key, value) {
        setForm((prev) => ({ ...prev, [key]: value }));
    }

    async function handleSave(e) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        const cleaned = { ...form };
        for (const key of NUMERIC_KEYS) {
            if (cleaned[key] === "" || cleaned[key] === undefined) cleaned[key] = null;
            else if (cleaned[key] !== null) cleaned[key] = Number(cleaned[key]);
        }

        try {
            const res = await fetch(`/api/admin/coins/${coinId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(cleaned),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Save failed");
            setMessage({ type: "success", text: "Coin updated successfully!" });
        } catch (err) {
            setMessage({ type: "error", text: err.message });
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return (
            <div className="loading-container small">
                <div className="spinner" />
            </div>
        );
    }

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">
                    Edit: {form.name || coinId}
                </h1>
                <button
                    onClick={() => router.push("/dashboard/coins")}
                    className="btn btn-secondary"
                >
                    ← Back to Coins
                </button>
            </div>

            {message && (
                <div className={`alert alert-${message.type}`}>{message.text}</div>
            )}

            <form onSubmit={handleSave}>
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
                                    <label htmlFor={field.key}>{field.label}</label>

                                    {field.type === "textarea" ? (
                                        <textarea
                                            id={field.key}
                                            value={form[field.key] ?? ""}
                                            onChange={(e) => handleChange(field.key, e.target.value)}
                                            rows={field.key === "description" ? 6 : 3}
                                        />
                                    ) : field.type === "checkbox" ? (
                                        <input
                                            id={field.key}
                                            type="checkbox"
                                            checked={!!form[field.key]}
                                            onChange={(e) =>
                                                handleChange(field.key, e.target.checked)
                                            }
                                        />
                                    ) : (
                                        <input
                                            id={field.key}
                                            type={field.type}
                                            step={field.type === "number" ? "any" : undefined}
                                            value={form[field.key] ?? ""}
                                            onChange={(e) => handleChange(field.key, e.target.value)}
                                            readOnly={field.readonly}
                                            className={field.readonly ? "readonly" : ""}
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
                        className="btn btn-primary"
                        disabled={saving}
                    >
                        {saving ? "Saving…" : "💾 Save Changes"}
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
