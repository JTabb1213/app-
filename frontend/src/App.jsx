import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "./pages/Home"
import CoinPage from "./pages/CoinPage"

function App() {
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
