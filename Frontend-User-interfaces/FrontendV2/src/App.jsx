import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "./pages/Home"
import CoinPage from "./pages/CoinPage"
import Search from "./pages/Search"
import Dashboard from "./pages/Dashboard"
import About from "./pages/About"
import Navbar from "./components/Navbar"
import Footer from "./components/Footer"

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/token/:coinId" element={<CoinPage />} />
        <Route path="/search" element={<Search />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/about" element={<About />} />
      </Routes>
      <Footer />
    </BrowserRouter>
  )
}

export default App
