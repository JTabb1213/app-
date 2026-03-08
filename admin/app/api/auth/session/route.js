import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth";

export async function GET() {
    const session = await requireAdmin();
    if (!session) {
        return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }
    return NextResponse.json({ username: session.username });
}
