/**
 * In-process alias resolver backed by data/coin_aliases.json.
 *
 * This is the admin (Next.js) equivalent of the Python resolver at
 * backend/services/alias/resolver.py.  Both read the same shared JSON file
 * at <project-root>/data/coin_aliases.json.
 *
 * The file is read from disk on each call — this is fine because:
 *   - It's a small file (~10-50 KB)
 *   - Only admin routes use it (not user-facing traffic)
 *   - It means edits to the JSON are picked up immediately with no restart
 */

import { readFileSync } from "fs";
import { join } from "path";

// Resolve relative to the project root.
// In Next.js, process.cwd() is the project root (where package.json is).
const ALIASES_PATH = join(process.cwd(), "data", "coin_aliases.json");

/**
 * Load and parse the alias JSON file.
 * Returns the parsed object or null on error.
 */
function loadAliasFile() {
    try {
        const raw = readFileSync(ALIASES_PATH, "utf-8");
        return JSON.parse(raw);
    } catch (err) {
        console.error(`[aliases] ✗ Failed to load ${ALIASES_PATH}: ${err.message}`);
        return null;
    }
}

/**
 * Build a flat lookup dict: lowercased alias → canonical ID.
 * Includes the canonical ID itself, all explicit aliases, and exchange symbols.
 */
function buildLookup(data) {
    const lookup = {};
    const assets = data?.assets || {};

    for (const [canonicalId, entry] of Object.entries(assets)) {
        // Canonical ID maps to itself
        lookup[canonicalId.toLowerCase()] = canonicalId;

        // All explicit aliases
        for (const alias of entry.aliases || []) {
            lookup[alias.toLowerCase()] = canonicalId;
        }

        // Exchange-specific symbols also serve as incoming aliases
        for (const sym of Object.values(entry.exchange_symbols || {})) {
            lookup[sym.toLowerCase()] = canonicalId;
        }
    }

    return lookup;
}

/**
 * Resolve any alias/symbol/name to its canonical coin ID.
 *
 * @param {string} term — case-insensitive search term
 * @returns {string|null} canonical coin ID or null
 *
 * @example
 *   resolveAlias("XBT")      // → "bitcoin"
 *   resolveAlias("btc")      // → "bitcoin"
 *   resolveAlias("Bitcoin")  // → "bitcoin"
 *   resolveAlias("unknown")  // → null
 */
export function resolveAlias(term) {
    if (!term) return null;
    const data = loadAliasFile();
    if (!data) return null;
    const lookup = buildLookup(data);
    return lookup[term.trim().toLowerCase()] ?? null;
}

/**
 * Get all canonical assets from the alias file.
 * Returns { [canonicalId]: { symbol, aliases, exchange_symbols, ... } }
 */
export function getAllAssets() {
    const data = loadAliasFile();
    return data?.assets || {};
}

/**
 * Get the total number of alias strings registered.
 */
export function getAliasStats() {
    const data = loadAliasFile();
    if (!data) return { assets: 0, aliases: 0 };
    const lookup = buildLookup(data);
    const assets = Object.keys(data.assets || {}).length;
    const aliases = Object.keys(lookup).length;
    return { assets, aliases, updated_at: data._meta?.updated_at };
}
