import pg from "pg";

// Re-use a single pool across hot-reloads in dev
const globalForPg = globalThis;

if (!globalForPg._pgPool) {
    globalForPg._pgPool = new pg.Pool({
        connectionString: process.env.DATABASE_URL,
        max: 5,
    });
}

/** @type {pg.Pool} */
const pool = globalForPg._pgPool;

export default pool;
