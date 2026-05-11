/**
 * WebSocket service for real-time price data.
 *
 * Connects to the WS broadcast server (ws/ folder) and manages
 * subscriptions to the "prices" channel. All components share a
 * single WebSocket connection via the exported singleton.
 *
 * Error handling:
 *   Every failure path produces a detailed, human-readable message
 *   explaining WHY the connection failed and what to check.
 */

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8765"

// ── Connection states ─────────────────────────────────────────────
export const ConnectionState = {
    CONNECTING: "connecting",
    CONNECTED: "connected",
    DISCONNECTED: "disconnected",
    ERROR: "error",
}

// ── WebSocket close-code → human-readable explanations ────────────
const CLOSE_CODE_MESSAGES = {
    1000: "Normal closure",
    1001: "Server going away (server shutting down or page navigated away)",
    1002: "Protocol error — the server rejected the WebSocket handshake",
    1003: "Unsupported data type received from the server",
    1005: "No status code received — the connection may have been blocked by a proxy",
    1006: "Abnormal closure — the connection was lost unexpectedly",
    1007: "Invalid payload data received",
    1008: "Policy violation — the server rejected the connection",
    1009: "Message too large — the server closed the connection",
    1010: "Missing expected extension",
    1011: "Internal server error on the WebSocket server",
    1012: "Service restart — the server is restarting",
    1013: "Try again later — the server is overloaded",
    1015: "TLS handshake failure — check that the SSL certificate is valid",
}

class WebSocketService {
    constructor() {
        this._ws = null
        this._listeners = new Map() // coin_id → Set<callback>
        this._stateListeners = new Set()
        this._state = ConnectionState.DISCONNECTED
        this._error = null
        this._reconnectTimer = null
        this._reconnectAttempts = 0
        this._maxReconnectAttempts = 10
        this._subscribedCoins = new Set()
        this._intentionalClose = false
    }

    // ── Public getters ────────────────────────────────────────────
    get state() {
        return this._state
    }
    get error() {
        return this._error
    }
    get isConnected() {
        return this._state === ConnectionState.CONNECTED
    }

    // ── Connect ───────────────────────────────────────────────────
    connect() {
        if (
            this._ws &&
            (this._ws.readyState === WebSocket.CONNECTING ||
                this._ws.readyState === WebSocket.OPEN)
        ) {
            return
        }

        this._intentionalClose = false
        this._setState(ConnectionState.CONNECTING)
        this._error = null

        console.log(`[WS] Connecting to ${WS_URL} ...`)

        try {
            this._ws = new WebSocket(WS_URL)
        } catch (err) {
            this._handleError(
                `Failed to create WebSocket connection: ${err.message}. ` +
                `URL attempted: ${WS_URL}. ` +
                `Check that VITE_WS_URL is set correctly in your .env file.`
            )
            return
        }

        // ── onopen ────────────────────────────────────────────────
        this._ws.onopen = () => {
            console.log("[WS] ✅ Connected to", WS_URL)
            this._reconnectAttempts = 0
            this._error = null
            this._setState(ConnectionState.CONNECTED)

            // Re-subscribe to any coins we were tracking before a reconnect
            if (this._subscribedCoins.size > 0) {
                this._sendSubscribe([...this._subscribedCoins])
            }
        }

        // ── onmessage ─────────────────────────────────────────────
        this._ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data)

                // Server-side error (bad subscribe request, etc.)
                if (msg.type === "error") {
                    console.warn("[WS] Server error:", msg.message)
                    return
                }

                // Subscription acknowledgements
                if (msg.type === "subscribed" || msg.type === "unsubscribed") {
                    console.log(
                        `[WS] ${msg.type}: ${msg.channel} → ${msg.coins?.join(", ")}`
                    )
                    return
                }

                // Price data — dispatch to registered callbacks
                if (msg.channel === "prices" && msg.data) {
                    const coinId = msg.data.coin_id

                    // End-to-end latency: time from Redis publish → browser receive
                    if (msg.data.published_at) {
                        const latencyMs = Date.now() - msg.data.published_at
                        console.log(`[WS latency] ${coinId}: ${latencyMs}ms`)
                    }

                    const callbacks = this._listeners.get(coinId)
                    if (callbacks) {
                        callbacks.forEach((cb) => cb(msg.data))
                    }
                }
            } catch (err) {
                console.error("[WS] Failed to parse incoming message:", err)
            }
        }

        // ── onerror ───────────────────────────────────────────────
        // Browser WebSocket error events intentionally lack detail
        // (security restriction). The subsequent onclose has real info.
        this._ws.onerror = () => {
            console.error("[WS] ❌ WebSocket error event (details in close event)")
        }

        // ── onclose ───────────────────────────────────────────────
        this._ws.onclose = (event) => {
            const reason = this._buildCloseReason(event)
            console.warn(`[WS] Connection closed: ${reason}`)

            if (this._intentionalClose) {
                this._setState(ConnectionState.DISCONNECTED)
                return
            }

            this._handleError(reason)
            this._scheduleReconnect()
        }
    }

    // ── Disconnect ────────────────────────────────────────────────
    disconnect() {
        this._intentionalClose = true
        clearTimeout(this._reconnectTimer)
        if (this._ws) {
            this._ws.close(1000, "Client disconnect")
            this._ws = null
        }
        this._setState(ConnectionState.DISCONNECTED)
        this._subscribedCoins.clear()
    }

    // ── Subscribe to a coin ───────────────────────────────────────
    /**
     * Subscribe to real-time price updates for a coin.
     * Returns an unsubscribe function.
     *
     * @param {string} coinId  Canonical coin ID (e.g. "bitcoin")
     * @param {Function} callback  Called with price data object on each tick
     * @returns {Function} Unsubscribe function
     */
    subscribe(coinId, callback) {
        // Register listener
        if (!this._listeners.has(coinId)) {
            this._listeners.set(coinId, new Set())
        }
        this._listeners.get(coinId).add(callback)

        // Track coin subscription
        const wasSubscribed = this._subscribedCoins.has(coinId)
        this._subscribedCoins.add(coinId)

        // Ensure we're connected
        if (!this._ws || this._ws.readyState !== WebSocket.OPEN) {
            this.connect()
        } else if (!wasSubscribed) {
            this._sendSubscribe([coinId])
        }

        // Return cleanup function
        return () => {
            const callbacks = this._listeners.get(coinId)
            if (callbacks) {
                callbacks.delete(callback)
                if (callbacks.size === 0) {
                    this._listeners.delete(coinId)
                    this._subscribedCoins.delete(coinId)
                    if (this._ws?.readyState === WebSocket.OPEN) {
                        this._sendUnsubscribe([coinId])
                    }
                }
            }
        }
    }

    // ── State change listener ─────────────────────────────────────
    /**
     * Register a callback for connection state changes.
     * Returns an unsubscribe function.
     */
    onStateChange(callback) {
        this._stateListeners.add(callback)
        return () => this._stateListeners.delete(callback)
    }

    // ── Internal helpers ──────────────────────────────────────────

    _sendSubscribe(coins) {
        if (this._ws?.readyState === WebSocket.OPEN) {
            this._ws.send(
                JSON.stringify({
                    action: "subscribe",
                    channel: "prices",
                    coins,
                })
            )
        }
    }

    _sendUnsubscribe(coins) {
        if (this._ws?.readyState === WebSocket.OPEN) {
            this._ws.send(
                JSON.stringify({
                    action: "unsubscribe",
                    channel: "prices",
                    coins,
                })
            )
        }
    }

    _setState(newState) {
        this._state = newState
        this._stateListeners.forEach((cb) => cb(newState, this._error))
    }

    _handleError(message) {
        this._error = message
        this._setState(ConnectionState.ERROR)
    }

    /**
     * Build a detailed, human-readable close reason from a CloseEvent.
     */
    _buildCloseReason(event) {
        const { code, reason, wasClean } = event
        const codeMsg = CLOSE_CODE_MESSAGES[code] || `Unknown close code: ${code}`
        const cleanStr = wasClean ? "clean" : "unclean (abnormal)"
        const serverReason = reason || "No reason provided by server"

        let detail = `WebSocket closed (code ${code}, ${cleanStr}): ${codeMsg}. Server reason: "${serverReason}".`

        // Add actionable diagnostics for the most common failure
        if (code === 1006) {
            detail +=
                `\n\nThis usually means one of:\n` +
                `  • The WebSocket server at ${WS_URL} is not running\n` +
                `  • A firewall or proxy is blocking WebSocket connections on the server's port\n` +
                `  • The VITE_WS_URL environment variable is incorrect\n` +
                `  • Network connectivity issue between your browser and the server`
        }

        return detail
    }

    _scheduleReconnect() {
        if (this._reconnectAttempts >= this._maxReconnectAttempts) {
            this._handleError(
                `Failed to reconnect after ${this._maxReconnectAttempts} attempts. ` +
                `The WebSocket server at ${WS_URL} appears to be unreachable. ` +
                `Please verify the server is running and refresh the page to try again.`
            )
            return
        }

        const backoff = Math.min(
            1000 * Math.pow(2, this._reconnectAttempts),
            30000
        )
        this._reconnectAttempts++

        console.log(
            `[WS] Reconnecting in ${backoff / 1000}s ` +
            `(attempt ${this._reconnectAttempts}/${this._maxReconnectAttempts})...`
        )

        this._reconnectTimer = setTimeout(() => {
            this.connect()
        }, backoff)
    }
}

// Singleton — all components share one WebSocket connection
export const wsService = new WebSocketService()
