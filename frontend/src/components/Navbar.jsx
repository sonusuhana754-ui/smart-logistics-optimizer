import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import axios from 'axios'

const NAV_ITEMS = [
  { to: '/',          icon: '⬡', label: 'Dashboard'         },
  { to: '/predict',   icon: '🧠', label: 'Prediction Studio'  },
  { to: '/routes',    icon: '🗺️', label: 'Route Optimizer'    },
  { to: '/shipments', icon: '📦', label: 'Shipment Planner'   },
  { to: '/analytics', icon: '📊', label: 'Analytics'          },
]

export default function Navbar() {
  const [rt, setRt] = useState(null)

  useEffect(() => {
    const fetchRt = async () => {
      try {
        const { data } = await axios.get('/api/realtime')
        setRt(data)
      } catch {}
    }
    fetchRt()
    const id = setInterval(fetchRt, 5000)
    return () => clearInterval(id)
  }, [])

  const trafficColor = rt
    ? rt.traffic_density > 70 ? 'var(--accent-red)'
    : rt.traffic_density > 45 ? 'var(--accent-amber)'
    : 'var(--accent-green)'
    : 'var(--accent-green)'

  const weatherIcon = rt
    ? { Clear: '☀️', Rain: '🌧️', Fog: '🌫️', Storm: '⛈️', Snow: '❄️' }[rt.weather_condition] ?? '☁️'
    : '☀️'

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="brand-icon">🚚</div>
        <div className="brand-text">
          <div className="brand-name">LogisticAI</div>
          <div className="brand-sub">Optimization System</div>
        </div>
      </div>

      <div className="navbar-section-label">Navigation</div>

      <div className="navbar-links">
        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
      </div>

      <div className="navbar-bottom">
        {rt && (
          <div style={{ marginBottom: 12, padding: '10px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
              Live Conditions
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{weatherIcon} {rt.weather_condition}</span>
              <span className="badge badge-green" style={{ fontSize: '0.6rem', padding: '2px 6px' }}>LIVE</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              Traffic
            </div>
            <div className="progress-bar-wrap" style={{ marginBottom: 2 }}>
              <div
                className="progress-bar-fill"
                style={{ width: `${rt.traffic_density}%`, background: trafficColor, transition: 'width 1s ease' }}
              />
            </div>
            <div style={{ fontSize: '0.7rem', color: trafficColor, fontWeight: 700 }}>
              {rt.traffic_density?.toFixed(0)}%
              {rt.anomaly_active && <span style={{ marginLeft: 6, color: 'var(--accent-red)' }}>⚡ ANOMALY</span>}
            </div>
          </div>
        )}
        <div className="live-indicator">
          <div className="live-dot" />
          <span>System Online</span>
        </div>
      </div>
    </nav>
  )
}
