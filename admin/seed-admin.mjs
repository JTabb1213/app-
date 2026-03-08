#!/usr/bin/env node
/**
 * Seed script — creates the admins table and inserts a default admin user.
 *
 * Usage:
 *   cd admin
 *   npm run seed
 */

import pg from "pg";
import bcrypt from "bcryptjs";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

// Load .env.local manually (dotenv isn't a dep, so we parse it simply)
const __dir = dirname(fileURLToPath(import.meta.url));
try {
    const env = readFileSync(resolve(__dir, ".env.local"), "utf-8");
    for (const line of env.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const idx = trimmed.indexOf("=");
        if (idx === -1) continue;
        const key = trimmed.slice(0, idx);
        const val = trimmed.slice(idx + 1);
        if (!process.env[key]) process.env[key] = val;
    }
} catch {
    // ignore missing file
}

const DATABASE_URL = process.env.DATABASE_URL;
if (!DATABASE_URL) {
    console.error("❌ DATABASE_URL not set. Create admin/.env.local first.");
    process.exit(1);
}

const pool = new pg.Pool({ connectionString: DATABASE_URL });

async function seed() {
    const client = await pool.connect();
    try {
        // Create table
        await client.query(`
      CREATE TABLE IF NOT EXISTS admins (
        id            SERIAL PRIMARY KEY,
        username      VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at    TIMESTAMPTZ DEFAULT NOW()
      )
    `);

        // Check if admin already exists
        const { rows } = await client.query(
            "SELECT id FROM admins WHERE username = 'admin'"
        );
        if (rows.length) {
            console.log("Admin user already exists — skipping.");
        } else {
            const hash = await bcrypt.hash("admin123", 10);
            await client.query(
                "INSERT INTO admins (username, password_hash) VALUES ($1, $2)",
                ["admin", hash]
            );
            console.log("✅ Created admin user");
            console.log("   Username: admin");
            console.log("   Password: admin123");
            console.log("   ⚠️  Change this password after first login!");
        }
    } catch (err) {
        console.error("❌ Error:", err.message);
        process.exit(1);
    } finally {
        client.release();
        await pool.end();
    }
}

seed();
