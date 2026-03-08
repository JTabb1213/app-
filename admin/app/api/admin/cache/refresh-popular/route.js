import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { setBulkTokenomics } from "@/lib/redis";
import { fetchTopCoins, mapMarketToTokenomics } from "@/lib/coingecko";

/**
 * POST /api/admin/cache/refresh-popular
 * Refresh tokenomics cache for the top 20 coins.
 */
export async function POST() {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        const raw = await fetchTopCoins(20);
        const entries = {};
        for (const coin of raw) {
            entries[coin.id] = mapMarketToTokenomics(coin);
        }
        const cached = await setBulkTokenomics(entries, 120);
        return NextResponse.json({
            success: true,
            total: raw.length,
            succeeded: cached,
            failed: 0,
        });
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
