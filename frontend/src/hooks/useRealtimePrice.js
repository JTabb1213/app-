import { useState, useEffect, useRef } from "react"
import { wsService, ConnectionState } from "../services/websocket"

/**
 * Custom hook for subscribing to real-time price data via WebSocket.
 *
 * Returns:
 *   priceData       — latest aggregate price data (or null)
 *   isConnected     — true when the WebSocket is open
 *   connectionState — one of: connecting, connected, disconnected, error
 *   error           — detailed error string (or null)
 *
 * Usage:
 *   const { priceData, isConnected, error } = useRealtimePrice("bitcoin")
 */
export function useRealtimePrice(coinId) {
    const [priceData, setPriceData] = useState(null)
    const [connectionState, setConnectionState] = useState(wsService.state)
    const [error, setError] = useState(wsService.error)
    const cleanupRef = useRef(null)

    useEffect(() => {
        if (!coinId) return

        // Sync initial state (the singleton may already be connected)
        setConnectionState(wsService.state)
        setError(wsService.error)

        // Listen for state changes on the shared WS connection
        const unsubState = wsService.onStateChange((state, err) => {
            setConnectionState(state)
            setError(err)
        })

        // Subscribe to price updates for this coin
        const unsubPrice = wsService.subscribe(coinId, (data) => {
            setPriceData(data)
        })

        cleanupRef.current = () => {
            unsubState()
            unsubPrice()
        }

        return () => {
            if (cleanupRef.current) {
                cleanupRef.current()
                cleanupRef.current = null
            }
            setPriceData(null)
        }
    }, [coinId])

    return {
        priceData,
        isConnected: connectionState === ConnectionState.CONNECTED,
        connectionState,
        error,
    }
}
