import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import pool from "@/lib/db";
import { getAlias } from "@/lib/redis";

/**
 * GET /api/admin/coins — list all coins from DB
 */
export async function GET() {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        const { rows } = await pool.query(
            "SELECT * FROM coins ORDER BY market_cap_rank ASC NULLS LAST LIMIT 1000"
        );
        return NextResponse.json({ coins: rows });
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}

/**
 * POST /api/admin/coins — create a new coin (with duplicate detection)
 */
export async function POST(req) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        const data = await req.json();
        const coinId = (data.id || "").toLowerCase().trim();
        if (!coinId) {
            return NextResponse.json({ error: "Coin ID is required" }, { status: 400 });
        }

        // Check alias collision
        const aliasMatch = await getAlias(coinId);
        if (aliasMatch) {
            const { rows } = await pool.query("SELECT id, name FROM coins WHERE id = $1", [aliasMatch]);
            if (rows[0]) {
                return NextResponse.json(
                    {
                        error: `'${coinId}' resolves to existing coin '${aliasMatch}' (${rows[0].name}). Use the edit page instead.`,
                        existing_coin: aliasMatch,
                    },
                    { status: 409 }
                );
            }
        }

        // Check direct DB match
        const { rows: existing } = await pool.query("SELECT id FROM coins WHERE id = $1", [coinId]);
        if (existing[0]) {
            return NextResponse.json(
                { error: `Coin '${coinId}' already exists in the database.`, existing_coin: coinId },
                { status: 409 }
            );
        }

        // Check symbol alias collision
        const symbol = (data.symbol || "").toLowerCase().trim();
        if (symbol) {
            const symMatch = await getAlias(symbol);
            if (symMatch && symMatch !== coinId) {
                return NextResponse.json(
                    {
                        error: `Symbol '${symbol}' is already mapped to '${symMatch}'. This would create confusion.`,
                        existing_coin: symMatch,
                    },
                    { status: 409 }
                );
            }
        }

        data.id = coinId;
        const row = await upsertCoin(data);
        return NextResponse.json({ success: true, coin: row }, { status: 201 });
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}

/* ------------------------------------------------------------------ */
/*  Shared upsert helper                                               */
/* ------------------------------------------------------------------ */

export async function upsertCoin(coin) {
    const d = {
        id: null, symbol: null, name: null, image_url: null, github_url: null,
        market_cap_rank: null, circulating_supply: null, total_supply: null,
        max_supply: null, fully_diluted_valuation: null,
        ath: null, ath_date: null, atl: null, atl_date: null,
        description: null, rating_score: null, rating_notes: null,
        review_count: null, is_featured: null,
        ...coin,
    };

    const { rows } = await pool.query(
        `INSERT INTO coins (
        id, symbol, name, image_url, github_url,
        market_cap_rank, circulating_supply, total_supply, max_supply,
        fully_diluted_valuation,
        ath, ath_date, atl, atl_date,
        description, rating_score, rating_notes, review_count, is_featured
     ) VALUES (
        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19
     )
     ON CONFLICT (id) DO UPDATE SET
        symbol                  = EXCLUDED.symbol,
        name                    = EXCLUDED.name,
        image_url               = EXCLUDED.image_url,
        github_url              = COALESCE(EXCLUDED.github_url, coins.github_url),
        market_cap_rank         = EXCLUDED.market_cap_rank,
        circulating_supply      = EXCLUDED.circulating_supply,
        total_supply            = EXCLUDED.total_supply,
        max_supply              = EXCLUDED.max_supply,
        fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
        ath                     = EXCLUDED.ath,
        ath_date                = EXCLUDED.ath_date,
        atl                     = EXCLUDED.atl,
        atl_date                = EXCLUDED.atl_date,
        description             = COALESCE(EXCLUDED.description, coins.description),
        rating_score            = COALESCE(EXCLUDED.rating_score, coins.rating_score),
        rating_notes            = COALESCE(EXCLUDED.rating_notes, coins.rating_notes),
        review_count            = COALESCE(EXCLUDED.review_count, coins.review_count),
        is_featured             = COALESCE(EXCLUDED.is_featured, coins.is_featured)
     RETURNING *`,
        [
            d.id, d.symbol, d.name, d.image_url, d.github_url,
            d.market_cap_rank, d.circulating_supply, d.total_supply, d.max_supply,
            d.fully_diluted_valuation,
            d.ath, d.ath_date, d.atl, d.atl_date,
            d.description, d.rating_score, d.rating_notes, d.review_count, d.is_featured,
        ]
    );
    return rows[0];
}
