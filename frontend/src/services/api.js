const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

export async function getTokenomics(coinId) {
    console.log(`[API] Fetching tokenomics for ${coinId}`)
    console.log(`[API] Full URL: ${BASE_URL}/tokenomics/${coinId}`)

    try {
        const res = await fetch(`${BASE_URL}/tokenomics/${coinId}`)
        console.log(`[API] Response status: ${res.status}`)

        if (!res.ok) {
            const errorData = await res.json()
            console.error(`[API] Error response:`, errorData)
            throw new Error("Tokenomics not found")
        }

        const data = await res.json()
        console.log(`[API] Success! Data:`, data)
        return data
    } catch (err) {
        console.error(`[API] Exception:`, err)
        throw err
    }
}

export async function getScore(coinId) {
    console.log(`[API] Fetching score for ${coinId}`)
    console.log(`[API] Full URL: ${BASE_URL}/score/${coinId}`)

    try {
        const res = await fetch(`${BASE_URL}/score/${coinId}`)
        console.log(`[API] Response status: ${res.status}`)

        if (!res.ok) {
            const errorData = await res.json()
            console.error(`[API] Error response:`, errorData)
            throw new Error("Score not found")
        }

        const data = await res.json()
        console.log(`[API] Success! Data:`, data)
        return data
    } catch (err) {
        console.error(`[API] Exception:`, err)
        throw err
    }
}

// ─── Database (static coin info) ────────────────────────────────────

export async function getCoinStatic(coinId) {
    console.log(`[API] Fetching static DB data for ${coinId}`)
    try {
        const res = await fetch(`${BASE_URL}/coins/${coinId}`)
        if (!res.ok) {
            const errorData = await res.json()
            console.error(`[API] DB error:`, errorData)
            return null // coin may not be in DB yet
        }
        const data = await res.json()
        console.log(`[API] Static data:`, data)
        return data
    } catch (err) {
        console.error(`[API] Exception fetching static data:`, err)
        return null
    }
}

export async function getTopCoinsStatic(limit = 50) {
    try {
        const res = await fetch(`${BASE_URL}/coins/top?limit=${limit}`)
        if (!res.ok) throw new Error("Failed to fetch top coins from DB")
        const data = await res.json()
        return data.coins || []
    } catch (err) {
        console.error(`[API] Exception:`, err)
        return []
    }
}

// ─── Volume (buy/sell pressure from Redis) ──────────────────────

export async function getVolume(coinId, window = "5m") {
    try {
        const res = await fetch(`${BASE_URL}/volume/${coinId}?window=${window}`)
        if (!res.ok) {
            const err = await res.json()
            throw new Error(err.error || "Volume not found")
        }
        return await res.json()
    } catch (err) {
        console.error(`[API] Volume fetch error:`, err)
        throw err
    }
}

// ─── Real-time cache update trigger ─────────────────────────────

// ─── Real-time cache update trigger ─────────────────────────────

export async function refreshRealtimeCache(limit = 50) {
    try {
        const res = await fetch(`${BASE_URL}/realtime/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ limit }),
        })
        return await res.json()
    } catch (err) {
        console.error(`[API] Exception refreshing cache:`, err)
        return { success: false, error: err.message }
    }
}

