const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

export async function getRating(coinId) {
    const res = await fetch(`${BASE_URL}/rating/${coinId}`)
    if (!res.ok) {
        if (res.status === 404) throw Object.assign(new Error("No rating data"), { status: 404 })
        throw new Error("Rating fetch failed")
    }
    return await res.json()
}

export async function getMarketData(coinId) {
    const res = await fetch(`${BASE_URL}/market/${coinId}`)
    if (!res.ok) {
        if (res.status === 404) throw Object.assign(new Error("No market data"), { status: 404 })
        throw new Error("Market fetch failed")
    }
    return await res.json()
}

export async function getNews(coinId) {
    const res = await fetch(`${BASE_URL}/news/${coinId}`)
    if (!res.ok) {
        if (res.status === 404) throw Object.assign(new Error("No news"), { status: 404 })
        throw new Error("News fetch failed")
    }
    return await res.json()
}

export async function getCandles(coinId, resolution = "1h", limit = 200) {
    const res = await fetch(`${BASE_URL}/candles/${coinId}?resolution=${resolution}&limit=${limit}`)
    if (!res.ok) {
        if (res.status === 404) throw Object.assign(new Error("No candle data"), { status: 404 })
        throw new Error("Candle fetch failed")
    }
    return await res.json()
}

export async function getVolume(coinId, window = "5m") {
    const res = await fetch(`${BASE_URL}/volume/${coinId}?window=${window}`)
    if (!res.ok) {
        if (res.status === 404) throw Object.assign(new Error("No volume data"), { status: 404 })
        throw new Error("Volume fetch failed")
    }
    return await res.json()
}
