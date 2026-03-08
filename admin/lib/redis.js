import Redis from "ioredis";

const globalForRedis = globalThis;

if (!globalForRedis._redis) {
    globalForRedis._redis = new Redis(process.env.REDIS_URL, { tls: {} });
}

/** @type {Redis} */
const redis = globalForRedis._redis;

export default redis;

/* ------------------------------------------------------------------ */
/*  Session helpers                                                    */
/* ------------------------------------------------------------------ */

const SESSION_TTL = 86400; // 24 h

export async function setSession(token, data) {
    await redis.setex(`session:${token}`, SESSION_TTL, JSON.stringify(data));
}

export async function getSession(token) {
    const raw = await redis.get(`session:${token}`);
    return raw ? JSON.parse(raw) : null;
}

export async function deleteSession(token) {
    await redis.del(`session:${token}`);
}

/* ------------------------------------------------------------------ */
/*  Alias helpers                                                      */
/* ------------------------------------------------------------------ */

export async function getAlias(term) {
    return redis.get(`crypto:alias:${term.toLowerCase()}`);
}

export async function setAlias(term, target, ttl = 604800) {
    await redis.setex(`crypto:alias:${term.toLowerCase()}`, ttl, target);
}

export async function deleteAlias(term) {
    await redis.del(`crypto:alias:${term.toLowerCase()}`);
}

export async function setBulkAliases(aliases, ttl = 604800) {
    const pipe = redis.pipeline();
    for (const [term, target] of Object.entries(aliases)) {
        pipe.setex(`crypto:alias:${term.toLowerCase()}`, ttl, target);
    }
    await pipe.exec();
    return Object.keys(aliases).length;
}

/* ------------------------------------------------------------------ */
/*  Tokenomics cache helpers                                           */
/* ------------------------------------------------------------------ */

export async function setTokenomics(coinId, data, ttl = 120) {
    const canonical = (await getAlias(coinId)) || coinId.toLowerCase();
    await redis.setex(
        `crypto:tokenomics:${canonical}`,
        ttl,
        JSON.stringify(data)
    );
}

export async function setBulkTokenomics(entries, ttl = 120) {
    const pipe = redis.pipeline();
    for (const [coinId, data] of Object.entries(entries)) {
        pipe.setex(`crypto:tokenomics:${coinId}`, ttl, JSON.stringify(data));
    }
    await pipe.exec();
    return Object.keys(entries).length;
}

export async function getCacheStats() {
    const info = await redis.info("memory");
    const memMatch = info.match(/used_memory_human:(\S+)/);
    const clients = await redis.info("clients");
    const clientMatch = clients.match(/connected_clients:(\d+)/);
    const keyCount = await redis.dbsize();

    return {
        connected: true,
        total_keys: keyCount,
        used_memory_human: memMatch ? memMatch[1] : "N/A",
        connected_clients: clientMatch ? Number(clientMatch[1]) : 0,
    };
}
