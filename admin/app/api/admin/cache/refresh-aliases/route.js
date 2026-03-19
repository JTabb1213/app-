import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { getAliasStats } from "@/lib/aliases";

/**
 * POST /api/admin/cache/refresh-aliases
 *
 * Alias rebuilding via CoinGecko API is no longer supported here.
 * To refresh aliases:
 *   1. Run: python tools/populate_aliases/main.py
 *   2. Restart the server (or POST /api/reload-aliases on the backend)
 *
 * This endpoint now returns current alias stats from the JSON file instead.
 */
export async function POST() {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const stats = getAliasStats();
    return NextResponse.json({
        success: false,
        message:
            "Alias rebuilding has moved offline. "
            + "Run 'python tools/populate_aliases/main.py' to refresh data/coin_aliases.json.",
        current_stats: stats,
    }, { status: 410 });
}
