/**
 * CoinGecko API helpers used by admin API routes.
 * No API key needed (free tier).
 */

const BASE = "https://api.coingecko.com/api/v3";
const TIMEOUT = 15_000; // ms

async function fetchJson(url) {
    const res = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT) });
    if (res.status === 429) throw new Error("CoinGecko rate limit exceeded");
    if (!res.ok) throw new Error(`CoinGecko ${res.status}: ${res.statusText}`);
    return res.json();
}

/* ------------------------------------------------------------------ */
/*  Full coin data (single coin)                                       */
/* ------------------------------------------------------------------ */

export async function fetchFullCoin(coinId) {
    return fetchJson(`${BASE}/coins/${coinId}`);
}

/**
 * Map a full /coins/{id} response → DB-friendly columns.
 */
export function mapFullCoinToDb(raw) {
    const md = raw.market_data || {};
    const links = raw.links || {};
    const ghRepos = (links.repos_url?.github || []).filter(Boolean);

    return {
        id: raw.id,
        symbol: raw.symbol,
        name: raw.name,
        image_url: raw.image?.large || null,
        github_url: ghRepos[0] || null,
        market_cap_rank: raw.market_cap_rank || null,
        circulating_supply: md.circulating_supply || null,
        total_supply: md.total_supply || null,
        max_supply: md.max_supply || null,
        fully_diluted_valuation: md.fully_diluted_valuation?.usd || null,
        ath: md.ath?.usd || null,
        ath_date: md.ath_date?.usd || null,
        atl: md.atl?.usd || null,
        atl_date: md.atl_date?.usd || null,
        description: raw.description?.en || null,
    };
}

/* ------------------------------------------------------------------ */
/*  Top coins by market cap                                            */
/* ------------------------------------------------------------------ */

export async function fetchTopCoins(perPage = 50, page = 1) {
    const url =
        `${BASE}/coins/markets?vs_currency=usd&order=market_cap_desc` +
        `&per_page=${perPage}&page=${page}&sparkline=false`;
    return fetchJson(url);
}

/**
 * Map a /coins/markets item → tokenomics cache object.
 */
export function mapMarketToTokenomics(coin) {
    return {
        name: coin.name,
        symbol: coin.symbol,
        current_price: coin.current_price,
        market_cap: coin.market_cap,
        total_volume: coin.total_volume,
        price_change_percentage_24h: coin.price_change_percentage_24h,
        circulating_supply: coin.circulating_supply,
        total_supply: coin.total_supply,
        max_supply: coin.max_supply,
    };
}

/* ------------------------------------------------------------------ */
/*  Full coins list (for alias building)                               */
/* ------------------------------------------------------------------ */

export async function fetchCoinsList() {
    return fetchJson(`${BASE}/coins/list`);
}
