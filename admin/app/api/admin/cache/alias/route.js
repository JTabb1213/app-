import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";

/**
 * POST /api/admin/cache/alias
 * Alias creation via API is no longer supported.
 * Edit data/coin_aliases.json directly, or run tools/populate_aliases/main.py.
 */
export async function POST() {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    return NextResponse.json(
        {
            error: "Aliases are now managed via data/coin_aliases.json. "
                + "Edit the JSON file directly, then restart the server "
                + "or call POST /api/reload-aliases on the backend.",
        },
        { status: 410 }
    );
}
