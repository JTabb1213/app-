import { BrowserRouter, Routes, Route } from "react-router-dom"
import { useEffect } from "react"
import Home from "./pages/Home"
import CoinPage from "./pages/CoinPage"

function App() {
  useEffect(() => {
    // Cache busting verification logs
    console.log("Frontend verification: hello")
    console.log("App version:", __APP_VERSION__ || "dev")
    console.log("Build time:", __BUILD_TIME__ ? new Date(__BUILD_TIME__).toISOString() : "dev")
    console.log("Build SHA:", import.meta.env.VITE_BUILD_SHA || "dev")
    console.log("Build number:", import.meta.env.VITE_BUILD_TIME || "dev")

    // Call backend verification endpoint
    fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8080"}/api/verify`)
      .then(res => res.json())
      .then(data => {
        console.log("Frontend backend connectivity: ✅ Connected")
        console.log("Hello from main API!", data.message)
        console.log("Backend response:", data)
      })
      .catch(err => {
        console.log("Frontend backend connectivity: ❌ Failed", err)
        console.log("Backend verification failed:", err)
      })
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/coin/:coinId" element={<CoinPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
