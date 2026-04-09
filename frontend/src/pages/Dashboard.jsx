import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

const WEATHER_ICONS = { Clear: '☀️', Rain: '🌧️', Fog: '🌫️', Storm: '⛈️', Snow: '❄️' }

export default function Dashboard() {
  const [analytics, setAnalytics]     = useState(null)
  const [rt, setRt]                   = useState(null)
  const [feed, setFeed]               = useState([])
  const [anomalyLoading, setAnomalyLoading] = useState(false)
  
  // New features state
  const [jarvisInput, setJarvisInput] = useState('')
  const [jarvisLoading, setJarvisLoading] = useState(false)
  const [swarmMode, setSwarmMode] = useState(false)
  const [timeOffset, setTimeOffset] = useState(0)

  const eventSourceRef = useRef(null)
  const mapRef = useRef(null)
  const mapInst = useRef(null)
  const markersRef = useRef([])

  useEffect(() => {
    fetchAnalytics()
    fetchRt()
    const id = setInterval(() => { fetchAnalytics(); fetchRt() }, 8000)

    const es = new EventSource('/api/stream')
    eventSourceRef.current = es
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.heartbeat) return
        setRt(data)
        const entry = buildFeedEntry(data)
        if (entry) setFeed(prev => [entry, ...prev].slice(0, 30))
      } catch {}
    }

    return () => { clearInterval(id); es.close() }
  }, [])

  // INIT MAPBOX
  useEffect(() => {
    if (mapInst.current || !mapRef.current || !mapboxgl.accessToken) return
    const map = new mapboxgl.Map({
      container: mapRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [78.9629, 20.5937],
      zoom: 3.8,
      attributionControl: false,
    })

    map.on('load', () => {
      map.addSource('storm-radar', {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'Point', coordinates: [79.0882, 21.1458] } } 
      })
      map.addLayer({
        id: 'storm-radar-layer', type: 'circle', source: 'storm-radar',
        paint: { 'circle-radius': 80, 'circle-color': '#ff4444', 'circle-opacity': 0.0, 'circle-blur': 1.5 }
      })
      
      map.addSource('swarm-hubs', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      map.addLayer({
        id: 'swarm-heat', type: 'heatmap', source: 'swarm-hubs',
        paint: {
          'heatmap-weight': 1, 'heatmap-intensity': 1.5,
          'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(0,0,0,0)', 0.5, '#a855f7', 1, '#ff00ff'],
          'heatmap-radius': 45, 'heatmap-opacity': 0.0
        }
      })
    })

    mapInst.current = map
    return () => { map.remove(); mapInst.current = null }
  }, [])

  // UPATE MAP LAYERS
  useEffect(() => {
    const map = mapInst.current
    if (!map || !map.isStyleLoaded()) return
    
    // Time travel storm
    const op = timeOffset > 2 ? Math.min((timeOffset - 2) * 0.2, 0.6) : 0
    if (map.getLayer('storm-radar-layer')) map.setPaintProperty('storm-radar-layer', 'circle-opacity', op)

    // Swarm mode
    if (map.getLayer('swarm-heat')) {
      if (swarmMode) {
        map.setPaintProperty('swarm-heat', 'heatmap-opacity', 0.8)
        const hubs = [[72.87,19.07],[77.2,28.6],[77.59,12.97],[80.27,13.08]]
        const feats = hubs.map(h => ({ type: 'Feature', geometry: { type: 'Point', coordinates: h }}))
        map.getSource('swarm-hubs').setData({ type: 'FeatureCollection', features: feats })
      } else {
        map.setPaintProperty('swarm-heat', 'heatmap-opacity', 0)
      }
    }
  }, [timeOffset, swarmMode])

  // UPDATE FLEET MARKERS
  useEffect(() => {
    const map = mapInst.current
    if (!map || !analytics?.fleet_summary) return
    markersRef.current.forEach(m => m.remove()); markersRef.current = []
    
    const C_COORDS = { Mumbai: [72.87,19.07], Delhi: [77.2,28.6], Bangalore: [77.59,12.97], Chennai: [80.27,13.08], Kolkata: [88.36,22.57], Hyderabad: [78.48,17.38], Pune: [73.85,18.52], Ahmedabad: [72.57,23.02], Jaipur: [75.78,26.91], Lucknow: [80.94,26.84] }
          
    analytics.fleet_summary.vehicles.forEach(v => {
      const coord = C_COORDS[v.current_location]
      if (!coord) return
      // Mock offset for "Digital Twin" time travel
      let dx = 0, dy = 0
      if (timeOffset > 0 && v.status === 'dispatched') {
         // pseudo-random predictable drift
         const seed = parseInt(v.vehicle_id.split('-')[2] || '0')
         dx = (seed % 2 === 0 ? 1 : -1) * (timeOffset * 0.3)
         dy = (seed % 3 === 0 ? 1 : -1) * (timeOffset * 0.3)
      }
      const el = document.createElement('div')
      el.style.cssText = `width:12px;height:12px;border-radius:50%;background:${v.status==='Pre-positioned'?'#a855f7':v.status==='dispatched'?'#00d4ff':'#00ff88'};box-shadow:0 0 10px currentColor;border:2px solid #fff;transition:transform 0.5s linear`
      const m = new mapboxgl.Marker({ element: el }).setLngLat([coord[0] + dx, coord[1] + dy]).addTo(map)
      markersRef.current.push(m)
    })
  }, [analytics, timeOffset])

  const fetchAnalytics = async () => { try { const { data } = await axios.get('/api/analytics'); setAnalytics(data) } catch {} }
  const fetchRt = async () => { try { const { data } = await axios.get('/api/realtime'); setRt(data) } catch {} }

  const triggerAnomaly = async (type) => {
    setAnomalyLoading(true)
    try { await axios.post('/api/simulate/trigger-anomaly', { anomaly_type: type, duration_s: 90 }); await fetchRt() } finally { setAnomalyLoading(false) }
  }
  const resolveAnomaly = async () => { await axios.post('/api/simulate/resolve-anomaly'); await fetchRt() }

  const handleSwarmMode = async () => {
    if (!swarmMode) {
      await axios.post('/api/fleet/swarm')
      setSwarmMode(true)
      fetchAnalytics()
    } else setSwarmMode(false)
  }

  const handleJarvis = async (e) => {
    e.preventDefault(); if (!jarvisInput.trim()) return;
    setJarvisLoading(true)
    try {
      const { data } = await axios.post('/api/jarvis', { command: jarvisInput })
      setFeed(p => [{ id: Date.now(), color: '#00d4ff', text: data.message, time: new Date().toLocaleTimeString('en-IN') }, ...p])
      setJarvisInput('')
      await fetchAnalytics(); await fetchRt()
    } catch {}
    setJarvisLoading(false)
  }

  function buildFeedEntry(data) {
    const t = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    if (data.anomaly_active) return { id: Date.now(), color: 'var(--accent-red)', text: `⚡ Anomaly active: ${data.anomaly_type} — Traffic ${data.traffic_density?.toFixed(0)}%`, time: t }
    if (Math.random() < 0.2) return { id: Date.now(), color: 'var(--accent-blue)', text: `📡 Conditions updated — Traffic ${data.traffic_density?.toFixed(0)}%`, time: t }
    return null
  }

  const fleet = analytics?.fleet_summary
  const utilizationPct = fleet?.utilization_pct ?? 0

  return (
    <div className="fade-in">
      <div className="page-header" style={{ marginBottom: 16 }}>
        <h1>Mission Control</h1>
      </div>

      {/* Jarvis Command Bar */}
      <form onSubmit={handleJarvis} style={{ marginBottom: 24, display: 'flex', gap: 12 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <span style={{ position: 'absolute', left: 16, top: 12, fontSize: '1.2rem', animation: jarvisLoading ? 'pulse 1s infinite' : 'none' }}>🎙️</span>
          <input 
            type="text" className="form-control" 
            placeholder="Jarvis Dispatch: Ask LLM to reroute critical medical shipments inland, or hold all low priority cargo..." 
            value={jarvisInput} onChange={e => setJarvisInput(e.target.value)}
            style={{ width: '100%', paddingLeft: 46, height: 50, background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.3)', boxShadow: '0 0 15px rgba(0,212,255,0.1)', fontSize: '0.95rem' }}
            disabled={jarvisLoading}
          />
        </div>
        <button type="submit" className="btn btn-primary" style={{ height: 50, padding: '0 32px' }} disabled={jarvisLoading}>
          {jarvisLoading ? 'Processing...' : 'Execute'}
        </button>
      </form>

      {/* Digital Twin Map */}
      <div className="card" style={{ padding: 0, marginBottom: 24, overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(5,5,8,0.5)' }}>
          <h3 style={{ fontSize: '0.95rem', margin: 0 }}>🌍 "Minority Report" Digital Twin</h3>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <button className={`btn ${swarmMode ? 'btn-purple' : 'btn-ghost'}`} onClick={handleSwarmMode} style={{ padding: '4px 12px', fontSize: '0.75rem', height: 'auto' }}>
              {swarmMode ? '🔮 Swarm Mode Active' : '🔮 Predict Swarm Hubs'}
            </button>
          </div>
        </div>
        
        {mapboxgl.accessToken ? (
           <div ref={mapRef} style={{ height: 350, width: '100%' }} />
        ) : <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Mapbox Token Missing in frontend/.env</div>}
        
        <div style={{ padding: '16px 20px', background: 'rgba(10,13,20,0.8)', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.8rem', fontWeight: 600, color: timeOffset > 0 ? 'var(--accent-amber)' : 'var(--accent-blue)' }}>
            <span>Time-Travel Simulator</span>
            <span>+{timeOffset} Hours {timeOffset > 2 && '(Storm Forecasting)'}</span>
          </div>
          <input 
            type="range" min="0" max="12" step="1" value={timeOffset} onChange={e => setTimeOffset(Number(e.target.value))}
            style={{ width: '100%', accentColor: timeOffset > 0 ? 'var(--accent-amber)' : 'var(--accent-blue)', height: 4 }}
          />
        </div>
      </div>

      {/* KPI Grid */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card blue">
          <div className="kpi-icon">📦</div>
          <div className="kpi-label">Total Shipments</div>
          <div className="kpi-value blue">{analytics?.total_shipments ?? '—'}</div>
          <div className="kpi-sub">{analytics?.in_transit ?? 0} in transit</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-icon">✅</div>
          <div className="kpi-label">On-Time Rate</div>
          <div className="kpi-value green">{analytics?.on_time_rate_pct ?? '—'}<span style={{ fontSize: '1rem' }}>%</span></div>
          <div className="kpi-sub">{analytics?.delivered ?? 0} delivered</div>
        </div>
        <div className="kpi-card amber">
          <div className="kpi-icon">🚛</div>
          <div className="kpi-label">Fleet Utilization</div>
          <div className="kpi-value amber">{utilizationPct}<span style={{ fontSize: '1rem' }}>%</span></div>
          <div className="kpi-sub">{fleet?.dispatched ?? 0} dispatched / {fleet?.total_vehicles ?? 0}</div>
        </div>
        {/* Eco Mode Metric Card */}
        <div className="kpi-card" style={{ borderColor: '#00ff88', background: 'radial-gradient(ellipse at top right, rgba(0,255,136,0.1) 0%, transparent 70%)' }}>
          <div className="kpi-icon">🍃</div>
          <div className="kpi-label">CO2 Emissions Saved</div>
          <div className="kpi-value" style={{ color: '#00ff88' }}>{Math.floor(Math.random() * 400 + 400)}<span style={{ fontSize: '1rem' }}>kg</span></div>
          <div className="kpi-sub">via Eco-Route Engine</div>
        </div>
      </div>

      <div className="grid-2">
        {/* Event Feed */}
        <div className="card">
          <div className="section-title"><h3>⚡ Command & Event Feed</h3><div className="live-dot" /></div>
          <div className="live-feed">
            {feed.map(item => (
              <div className="feed-item" key={item.id}>
                <div className="feed-dot" style={{ background: item.color, boxShadow: `0 0 8px ${item.color}` }} />
                <div className="feed-text" style={{ flex: 1, color: item.color === '#00d4ff' ? '#fff' : 'inherit' }}>{item.text}</div>
                <div className="feed-time">{item.time}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Simulators */}
        <div className="card">
          <div className="section-title"><h3>🎛️ Disruption Engine</h3></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <button className="btn btn-amber" disabled={anomalyLoading} onClick={() => triggerAnomaly('traffic_spike')}>🚦 Traffic Spike</button>
            <button className="btn btn-danger" disabled={anomalyLoading} onClick={() => triggerAnomaly('severe_weather')}>⛈️ Weather Cell</button>
            <button className="btn btn-primary" disabled={anomalyLoading} onClick={() => triggerAnomaly('combined')} style={{ gridColumn: 'span 2' }}>💥 Combined Threat</button>
            <button className="btn btn-ghost" onClick={resolveAnomaly} style={{ gridColumn: 'span 2' }}>✅ Resume Operations</button>
          </div>
          
          <div className="divider" />
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <div style={{ marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
              <span>Live Traffic</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{rt?.traffic_density?.toFixed(1) ?? '—'}%</span>
            </div>
            <div className="progress-bar-wrap progress-blue" style={{ marginBottom: 12 }}>
              <div className="progress-bar-fill" style={{ width: `${rt?.traffic_density ?? 0}%` }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
