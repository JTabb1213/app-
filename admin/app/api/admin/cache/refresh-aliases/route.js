import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { setBulkAliases } from "@/lib/redis";
import { fetchCoinsList, fetchTopCoins } from "@/lib/coingecko";

/**
 * POST /api/admin/cache/refresh-aliases
 * Rebuild all alias mappings (market-cap priority).
 */
export async function POST() {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        // 1. Fetch full coins list
        const coins = await fetchCoinsList();
        if (!coins?.length) {
            return NextResponse.json({ error: "Failed to fetch coins list" }, { status: 500 });
        }

        // 2. Build priority symbol map from top-500 by market cap
        const prioritySymbols = {};
        for (let page = 1; page <= 2; page++) {
            try {
                const top = await fetchTopCoins(250, page);
                for (const coin of top) {
                    const sym = coin.symbol?.toLowerCase();
                    if (sym && coin.id && !(sym in prioritySymbols)) {
                        prioritySymbols[sym] = coin.id;
                    }
                }
            } catch {
                break;
            }
        }

        // 3. Build alias dict
        const aliases = {};
        for (const coin of coins) {
            const coinId = coin.id;
            const symbol = (coin.symbol || "").toLowerCase();
            const name = coin.name;
            if (!coinId) continue;

            aliases[coinId] = coinId;

            if (symbol) {
                if (symbol in prioritySymbols) {
                    aliases[symbol] = prioritySymbols[symbol];
                } else if (!(symbol in aliases)) {
                    aliases[symbol] = coinId;
                }
            }

            if (name && !(name in aliases)) {
                aliases[name] = coinId;
            }
        }

        // 4. Bulk insert
        const count = await setBulkAliases(aliases, 604800);

        return NextResponse.json({
            success: true,
            aliases_updated: count,
            coins_processed: coins.length,
        });
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
