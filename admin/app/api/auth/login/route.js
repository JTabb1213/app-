import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import bcrypt from "bcryptjs";
import pool from "@/lib/db";
import { setSession } from "@/lib/redis";

export async function POST(req) {
    try {
        const { username, password } = await req.json();
        if (!username || !password) {
            return NextResponse.json(
                { error: "Username and password are required" },
                { status: 400 }
            );
        }

        const { rows } = await pool.query(
            "SELECT id, username, password_hash FROM admins WHERE username = $1",
            [username]
        );
        const admin = rows[0];

        if (!admin || !(await bcrypt.compare(password, admin.password_hash))) {
            return NextResponse.json(
                { error: "Invalid username or password" },
                { status: 401 }
            );
        }

        const token = randomUUID();
        await setSession(token, { admin_id: admin.id, username: admin.username });

        const res = NextResponse.json({ success: true, username: admin.username });
        res.cookies.set("admin_session", token, {
            httpOnly: true,
            sameSite: "lax",
            maxAge: 86400,
            path: "/",
        });
        return res;
    } catch (err) {
        console.error("[auth/login]", err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
