const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

export async function getTokenomics(coinId) {
    try {
        const res = await fetch(`${BASE_URL}/tokenomics/${coinId}`)
        if (!res.ok) throw new Error("Tokenomics not found")
        return await res.json()
    } catch (err) {
        throw err
    }
}

export async function getCoinStatic(coinId) {
    try {
        const res = await fetch(`${BASE_URL}/coins/${coinId}`)
        if (!res.ok) return null
        return await res.json()
    } catch (err) {
        return null
    }
}

export async function getVolume(coinId, window = "5m") {
    try {
        const res = await fetch(`${BASE_URL}/volume/${coinId}?window=${window}`)
        if (!res.ok) {
            const err = await res.json()
            throw new Error(err.error || "Volume not found")
        }
        return await res.json()
    } catch (err) {
        throw err
    }
}

export async function getCandles(coinId, resolution = "1h", limit = 200) {
    const res = await fetch(`${BASE_URL}/candles/${coinId}?resolution=${resolution}&limit=${limit}`)
    if (!res.ok) {
        if (res.status === 404) throw Object.assign(new Error("No candle data"), { status: 404 })
        throw new Error("Candle fetch failed")
    }
    return await res.json()
}
