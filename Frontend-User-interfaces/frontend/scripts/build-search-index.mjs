/**
 * Build script — generates a lightweight search index for the frontend
 * from the shared data/coin_aliases.json.
 *
 * Run:  node frontend/scripts/build-search-index.mjs
 *
 * Output: frontend/public/coin-search-index.json
 *
 * The output is a small array of objects with only the fields the
 * frontend needs for autocomplete:
 *   [
 *     { "id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "aliases": ["btc","xbt"] },
 *     ...
 *   ]
 */

import { readFileSync, writeFileSync, mkdirSync } from "fs"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "..", "..")

const aliasPath = join(ROOT, "data", "coin_aliases.json")
const outDir = join(ROOT, "frontend", "public")
const outPath = join(outDir, "coin-search-index.json")

const raw = JSON.parse(readFileSync(aliasPath, "utf-8"))
const assets = raw.assets || {}

/** Capitalise "usd-coin" → "Usd Coin", "bitcoin" → "Bitcoin" */
function titleCase(str) {
    return str
        .replace(/-/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase())
}

const index = Object.entries(assets)
    .map(([id, entry]) => ({
        id,
        symbol: entry.symbol || "",
        name: titleCase(id),
        // Merge aliases + exchange symbol values for maximum search coverage
        aliases: [
            ...new Set([
                ...(entry.aliases || []).map((a) => a.toLowerCase()),
                ...Object.values(entry.exchange_symbols || {}).map((s) => s.toLowerCase()),
            ]),
        ],
    }))
    .sort((a, b) => a.name.localeCompare(b.name))

mkdirSync(outDir, { recursive: true })
writeFileSync(outPath, JSON.stringify(index, null, 2))

console.log(`✅ Search index written to ${outPath} (${index.length} coins)`)
