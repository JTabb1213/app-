import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import pool from "@/lib/db";
import { upsertCoin } from "../route.js";

/**
 * GET /api/admin/coins/[coinId]
 */
export async function GET(_req, { params }) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { coinId } = await params;
    try {
        const { rows } = await pool.query("SELECT * FROM coins WHERE id = $1", [coinId.toLowerCase()]);
        if (!rows[0]) {
            return NextResponse.json({ error: `Coin '${coinId}' not found` }, { status: 404 });
        }
        return NextResponse.json(rows[0]);
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}

/**
 * PUT /api/admin/coins/[coinId]
 */
export async function PUT(req, { params }) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { coinId } = await params;
    try {
        const data = await req.json();
        data.id = coinId.toLowerCase();
        const row = await upsertCoin(data);
        return NextResponse.json({ success: true, coin: row });
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
