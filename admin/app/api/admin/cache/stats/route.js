import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";
import { getCacheStats } from "@/lib/redis";

export async function GET() {
    const session = await requireAdmin();
    if (!session) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    try {
        const stats = await getCacheStats();
        return NextResponse.json(stats);
    } catch (err) {
        return NextResponse.json({ connected: false, error: err.message });
    }
}
