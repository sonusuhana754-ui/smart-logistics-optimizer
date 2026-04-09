import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import PredictionStudio from './pages/PredictionStudio'
import RouteOptimizer from './pages/RouteOptimizer'
import ShipmentPlanner from './pages/ShipmentPlanner'
import Analytics from './pages/Analytics'

export default function App() {
  return (
    <div className="app-layout">
      <div className="mesh-bg" />
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/"              element={<Dashboard />} />
          <Route path="/predict"       element={<PredictionStudio />} />
          <Route path="/routes"        element={<RouteOptimizer />} />
          <Route path="/shipments"     element={<ShipmentPlanner />} />
          <Route path="/analytics"     element={<Analytics />} />
        </Routes>
      </main>
    </div>
  )
}
