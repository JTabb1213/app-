import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { setAlias } from "@/lib/redis";

/**
 * POST /api/admin/cache/alias
 * Create or overwrite an alias mapping.
 */
export async function POST(req) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        const { term, target } = await req.json();
        if (!term?.trim() || !target?.trim()) {
            return NextResponse.json(
                { error: "Both 'term' and 'target' are required" },
                { status: 400 }
            );
        }

        await setAlias(term.trim(), target.trim().toLowerCase(), 604800);
        return NextResponse.json({
            success: true,
            term: term.trim().toLowerCase(),
            target: target.trim().toLowerCase(),
        });
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
