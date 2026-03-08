import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { setTokenomics } from "@/lib/redis";
import { fetchFullCoin } from "@/lib/coingecko";

/**
 * POST /api/admin/cache/refresh-coin
 * Refresh tokenomics cache for a single coin.
 */
export async function POST(req) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        const { coin_id } = await req.json();
        if (!coin_id) {
            return NextResponse.json({ error: "coin_id is required" }, { status: 400 });
        }

        const raw = await fetchFullCoin(coin_id.trim().toLowerCase());
        const md = raw.market_data || {};

        const tokenomics = {
            name: raw.name,
            symbol: raw.symbol,
            current_price: md.current_price?.usd ?? null,
            market_cap: md.market_cap?.usd ?? null,
            total_volume: md.total_volume?.usd ?? null,
            price_change_percentage_24h: md.price_change_percentage_24h ?? null,
            circulating_supply: md.circulating_supply ?? null,
            total_supply: md.total_supply ?? null,
            max_supply: md.max_supply ?? null,
        };

        await setTokenomics(coin_id, tokenomics, 120);

        return NextResponse.json({
            coin_id,
            tokenomics_updated: true,
            errors: [],
        });
    } catch (err) {
        return NextResponse.json({
            coin_id: "unknown",
            tokenomics_updated: false,
            errors: [err.message],
        });
    }
}
