const BASE_URL = "http://localhost:8000/api"

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
