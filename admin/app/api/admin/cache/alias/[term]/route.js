import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { getAlias, deleteAlias } from "@/lib/redis";

/**
 * GET /api/admin/cache/alias/[term] — look up what a term resolves to
 */
export async function GET(_req, { params }) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { term } = await params;
    const resolved = await getAlias(term);
    return NextResponse.json({ term, resolved_to: resolved });
}

/**
 * DELETE /api/admin/cache/alias/[term] — delete an alias
 */
export async function DELETE(_req, { params }) {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { term } = await params;
    await deleteAlias(term);
    return NextResponse.json({ success: true, deleted: term });
}
