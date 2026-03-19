import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { resolveAlias } from "@/lib/aliases";
import { fetchFullCoin, mapFullCoinToDb } from "@/lib/coingecko";

/**
 * GET /api/admin/autofill/[coinId]
 * Fetch coin data from CoinGecko for form auto-fill (does NOT save).
 */
export async function GET(_req, { params }) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { coinId } = await params;
    try {
        const canonical = resolveAlias(coinId) || coinId.toLowerCase();
        const raw = await fetchFullCoin(canonical);
        const mapped = mapFullCoinToDb(raw);
        return NextResponse.json(mapped);
    } catch (err) {
        const status = err.message.includes("rate limit") ? 429 : 400;
        return NextResponse.json({ error: err.message }, { status });
    }
}
