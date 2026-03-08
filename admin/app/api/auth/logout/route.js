import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { deleteSession } from "@/lib/redis";

export async function POST() {
    const cookieStore = await cookies();
    const token = cookieStore.get("admin_session")?.value;
    if (token) await deleteSession(token);

    const res = NextResponse.json({ success: true });
    res.cookies.delete("admin_session");
    return res;
}
