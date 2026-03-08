import { cookies } from "next/headers";
import { getSession } from "./redis.js";

/**
 * Check the admin session from the request cookies.
 * Returns the session object or null.
 */
export async function requireAdmin() {
    const cookieStore = await cookies();
    const token = cookieStore.get("admin_session")?.value;
    if (!token) return null;
    return getSession(token);
}
