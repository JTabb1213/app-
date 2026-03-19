import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { resolveAlias } from "@/lib/aliases";

/**
 * GET /api/admin/cache/alias/[term] — look up what a term resolves to
 * Now reads from data/coin_aliases.json instead of Redis.
 */
export async function GET(_req, { params }) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { term } = await params;
    const resolved = resolveAlias(term);
    return NextResponse.json({ term, resolved_to: resolved });
}

/**
 * DELETE /api/admin/cache/alias/[term]
 * Alias deletion is no longer supported via API.
 * Edit data/coin_aliases.json directly.
 */
export async function DELETE() {
    return NextResponse.json(
        {
            error: "Aliases are now managed via data/coin_aliases.json. "
                + "Edit the file directly and restart, or POST /api/admin/cache/reload-aliases.",
        },
        { status: 410 }
    );
}
