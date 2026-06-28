import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import mapboxgl from 'mapbox-gl'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import 'mapbox-gl/dist/mapbox-gl.css'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'

const API = "https://empowering-acceptance-production-e364.up.railway.app";

const CITIES = ['Mumbai','Delhi','Bangalore','Chennai','Kolkata','Hyderabad','Pune',
  'Ahmedabad','Jaipur','Lucknow','Surat','Kochi','Bhubaneswar','Coimbatore',
  'Goa','Chandigarh','Nagpur','Indore','Bhopal','Visakhapatnam']

const MODES = [
  { key: 'balanced',  label: '⚖️ Balanced',  desc: 'Time + Cost + Distance' },
  { key: 'time',      label: '⚡ Fastest',    desc: 'Minimize travel time'   },
  { key: 'distance',  label: '📏 Shortest',   desc: 'Minimize distance'      },
  { key: 'cost',      label: '💰 Cheapest',   desc: 'Minimize cost'          },
]

const ROUTE_STYLES = {
  primary: { color: '#00d4ff', width: 5,   opacity: 1.0 },
  alt1:    { color: '#ffaa00', width: 3,   opacity: 0.7 },
  alt2:    { color: '#a855f7', width: 3,   opacity: 0.7 },
}

// City coords for Mapbox markers
const CITY_COORDS = {
  Mumbai:        [72.8777, 19.0760],
  Delhi:         [77.2090, 28.6139],
  Bangalore:     [77.5946, 12.9716],
  Chennai:       [80.2707, 13.0827],
  Kolkata:       [88.3639, 22.5726],
  Hyderabad:     [78.4867, 17.3850],
  Pune:          [73.8567, 18.5204],
  Ahmedabad:     [72.5714, 23.0225],
  Jaipur:        [75.7873, 26.9124],
  Lucknow:       [80.9462, 26.8467],
  Surat:         [72.8311, 21.1702],
  Kochi:         [76.2673,  9.9312],
  Bhubaneswar:   [85.8245, 20.2961],
  Coimbatore:    [76.9558, 11.0168],
  Goa:           [74.1240, 15.2993],
  Chandigarh:    [76.7794, 30.7333],
  Nagpur:        [79.0882, 21.1458],
  Indore:        [75.8577, 22.7196],
  Bhopal:        [77.4126, 23.2599],
  Visakhapatnam: [83.2185, 17.6868],
}

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

export default function RouteOptimizer() {
  const [form, setForm] = useState({
    origin: 'Mumbai', destination: 'Delhi', mode: 'balanced', delay_probability: 0, eco_mode: false,
  })
  const [avoidBbox, setAvoidBbox] = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [result,   setResult]   = useState(null)
  const [error,    setError]    = useState(null)
  const [rt,       setRt]       = useState(null)
  const [selected, setSelected] = useState('primary')

  const mapRef    = useRef(null)
  const mapInst   = useRef(null)
  const markersRef = useRef([])
  const layerIds   = useRef([])
  const sourceIds  = useRef([])

  // Load live conditions
  useEffect(() => {
    const fetch = () => axios.get(`${API}/api/realtime`).then(r => setRt(r.data)).catch(() => {})
    fetch()
    const id = setInterval(fetch, 5000)
    return () => clearInterval(id)
  }, [])

  // Init Mapbox map
  useEffect(() => {
    if (mapInst.current || !mapRef.current) return

    if (!mapboxgl.accessToken) {
      console.warn('No Mapbox token — map disabled.')
      return
    }

    const map = new mapboxgl.Map({
      container: mapRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [78.9629, 20.5937],
      zoom: 4.2,
      attributionControl: false,
    })

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right')

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: { polygon: true, trash: true },
      defaultMode: 'draw_polygon'
    })
    map.addControl(draw, 'top-left')

    map.on('draw.create', (e) => updateBbox(e, draw))
    map.on('draw.delete', () => setAvoidBbox(null))
    map.on('draw.update', (e) => updateBbox(e, draw))

    function updateBbox(e, drawInst) {
      const data = drawInst.getAll()
      if (data.features.length > 0) {
        // Just take the first polygon's bounding box
        const coords = data.features[0].geometry.coordinates[0]
        const lons = coords.map(c => c[0])
        const lats = coords.map(c => c[1])
        setAvoidBbox([Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)])
      } else {
        setAvoidBbox(null)
      }
    }

    mapInst.current = map
    return () => { map.remove(); mapInst.current = null }
  }, [])

  // Draw routes when result changes
  useEffect(() => {
    const map = mapInst.current
    if (!map || !result) return

    const doRender = () => {
      // Clean up previous layers/sources/markers
      layerIds.current.forEach(id => { if (map.getLayer(id)) map.removeLayer(id) })
      sourceIds.current.forEach(id => { if (map.getSource(id)) map.removeSource(id) })
      markersRef.current.forEach(m => m.remove())
      layerIds.current = []
      sourceIds.current = []
      markersRef.current = []

      const routes = [
        { key: 'primary', data: result.primary_route,     ...ROUTE_STYLES.primary },
        { key: 'alt1',    data: result.alternatives?.[0], ...ROUTE_STYLES.alt1    },
        { key: 'alt2',    data: result.alternatives?.[1], ...ROUTE_STYLES.alt2    },
      ]

      const bounds = new mapboxgl.LngLatBounds()
      let boundsEmpty = true

      routes.forEach(({ key, data, color, width, opacity }) => {
        if (!data?.waypoints?.length) return

        const coords = data.waypoints
          .map(w => CITY_COORDS[w.city])
          .filter(Boolean)

        if (!coords.length) return

        // Hit Mapbox Directions API for real road polylines
        const coordString = coords.map(c => c.join(',')).join(';')
        
        const srcId = `route-source-${key}`;
        const layId = `route-layer-${key}`;

        fetch(`https://api.mapbox.com/directions/v5/mapbox/driving/${coordString}?geometries=geojson&access_token=${mapboxgl.accessToken}`)
          .then(res => res.json())
          .then(data => {
            const geometry = data.routes?.[0]?.geometry || { type: 'LineString', coordinates: coords }
            
            map.addSource(srcId, {
              type: 'geojson',
              data: { type: 'Feature', geometry: geometry },
            })
            sourceIds.current.push(srcId)

            // Route line
            map.addLayer({
              id: layId,
              type: 'line',
              source: srcId,
              layout: { 'line-join': 'round', 'line-cap': 'round' },
              paint: {
                'line-color': color,
                'line-width': width,
                'line-opacity': opacity,
                ...(key !== 'primary' ? { 'line-dasharray': [4, 3] } : {}),
              },
            })
            layerIds.current.push(layId)

            // Glow layer for primary
            if (key === 'primary') {
              map.addLayer({
                id: `${layId}-glow`,
                type: 'line',
                source: srcId,
                layout: { 'line-join': 'round', 'line-cap': 'round' },
                paint: {
                  'line-color': color,
                  'line-width': width + 6,
                  'line-opacity': 0.12,
                  'line-blur': 4,
                },
              }, layId)
              layerIds.current.push(`${layId}-glow`)
            }
          })
          .catch(err => console.error("Directions API failed", err))



        // Markers
        data.waypoints.forEach((w, i) => {
          const coord = CITY_COORDS[w.city]
          if (!coord) return

          const isFirst = i === 0
          const isLast  = i === data.waypoints.length - 1

          const el = document.createElement('div')
          el.style.cssText = `
            width: ${isFirst || isLast ? 14 : 9}px;
            height: ${isFirst || isLast ? 14 : 9}px;
            border-radius: 50%;
            background: ${isFirst ? '#00ff88' : isLast ? '#ff4466' : color};
            border: 2px solid rgba(255,255,255,0.6);
            box-shadow: 0 0 ${isFirst || isLast ? 10 : 5}px ${isFirst ? '#00ff88' : isLast ? '#ff4466' : color};
            cursor: pointer;
          `

          const popup = new mapboxgl.Popup({ offset: 14, closeButton: false })
            .setHTML(`
              <div style="font-family:Inter,sans-serif;padding:4px 6px;background:#0d1117;border-radius:6px;min-width:90px">
                <div style="font-weight:700;color:${isFirst ? '#00ff88' : isLast ? '#ff4466' : '#00d4ff'};font-size:12px">${w.city}</div>
                <div style="color:#8b9ab5;font-size:10px;margin-top:2px">${w.lat?.toFixed(3)}°N ${w.lon?.toFixed(3)}°E</div>
              </div>
            `)

          const marker = new mapboxgl.Marker({ element: el })
            .setLngLat(coord)
            .setPopup(popup)
            .addTo(map)

          markersRef.current.push(marker)
          bounds.extend(coord)
          boundsEmpty = false
        })
      })

      if (!boundsEmpty) {
        map.fitBounds(bounds, { padding: 60, maxZoom: 8, duration: 1200 })
      }
    }

    // Wait for map style to be loaded
    if (map.isStyleLoaded()) {
      doRender()
    } else {
      map.once('load', doRender)
    }
  }, [result])

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null)
    try {
      const { data } = await axios.post(`${API}/api/optimize-route`, {
        origin: form.origin,
        destination: form.destination,
        optimization_mode: form.mode,
        delay_probability: Number(form.delay_probability),
        eco_mode: form.eco_mode,
        avoid_bbox: avoidBbox,
      })
      if (data.error) { setError(data.error); return }
      setResult(data)
      setSelected('primary')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Route optimization failed — is the backend running?')
    } finally { setLoading(false) }
  }

  const activeRoute = selected === 'primary' ? result?.primary_route
    : selected === 'alt1' ? result?.alternatives?.[0]
    : result?.alternatives?.[1]

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>🗺️ Route Optimizer</h1>
        <p>Dijkstra + A* pathfinding with dynamic re-routing. Powered by Mapbox GL JS dark map.</p>
      </div>

      {result?.rerouted_due_to_anomaly && (
        <div className="alert alert-amber mb-24">
          <span>↺</span>
          <span>Dynamic re-routing engaged — delay probability exceeded 60%. Switched to A* time-first algorithm.</span>
        </div>
      )}

      {/* Mapbox Map — full bleed card */}
      <div className="card" style={{ padding: 0, marginBottom: 24, overflow: 'hidden' }}>
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 8,
        }}>
          <h3 style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            🗺️ Route Visualization
            {rt?.anomaly_active && <span className="badge badge-red">⚡ ANOMALY</span>}
          </h3>
          <div style={{ display: 'flex', gap: 16, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span style={{ color: '#00d4ff' }}>━━ Primary</span>
            <span style={{ color: '#ffaa00' }}>╌╌ Alt-1 Shortest</span>
            <span style={{ color: '#a855f7' }}>╌╌ Alt-2 Fastest</span>
          </div>
        </div>

        {!mapboxgl.accessToken ? (
          <div style={{ height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 10, background: 'var(--bg-deep)' }}>
            <div style={{ fontSize: '2rem' }}>🗺️</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Mapbox token missing — add <code style={{ color: 'var(--accent-blue)' }}>VITE_MAPBOX_TOKEN</code> to <code>frontend/.env</code>
            </div>
          </div>
        ) : (
          <div ref={mapRef} style={{ height: 440, width: '100%' }} />
        )}
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Form */}
        <div className="card">
          <div className="section-title">
            <h3>🔧 Route Parameters</h3>
            {rt && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {rt.weather_condition} · Traffic {rt.traffic_density?.toFixed(0)}%
            </span>}
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Origin</label>
                <select className="form-control" value={form.origin} onChange={e => set('origin', e.target.value)}>
                  {CITIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Destination</label>
                <select className="form-control" value={form.destination} onChange={e => set('destination', e.target.value)}>
                  {CITIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Optimization Mode</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {MODES.map(m => (
                  <button key={m.key} type="button" onClick={() => set('mode', m.key)}
                    style={{
                      padding: '10px 12px', borderRadius: 8, border: '1px solid',
                      borderColor: form.mode === m.key ? 'var(--accent-blue)' : 'var(--border)',
                      background: form.mode === m.key ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.02)',
                      color: form.mode === m.key ? 'var(--accent-blue)' : 'var(--text-secondary)',
                      cursor: 'pointer', textAlign: 'left', transition: 'var(--transition)',
                    }}>
                    <div style={{ fontWeight: 600, fontSize: '0.82rem' }}>{m.label}</div>
                    <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>{m.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px', background: form.eco_mode ? 'rgba(0,255,136,0.1)' : 'rgba(255,255,255,0.02)', borderRadius: 8, border: `1px solid ${form.eco_mode ? '#00ff88' : 'var(--border)'}`, cursor: 'pointer', transition: 'var(--transition)' }} onClick={() => set('eco_mode', !form.eco_mode)}>
              <div style={{ fontSize: '1.5rem' }}>🍃</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: form.eco_mode ? '#00ff88' : 'var(--text-primary)' }}>Eco-Route Engine</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Minimize carbon footprint & fuel consumption</div>
              </div>
              <div className="toggle-switch" style={{ background: form.eco_mode ? '#00ff88' : '#333', width: 36, height: 20, borderRadius: 10, position: 'relative' }}>
                <div style={{ position: 'absolute', top: 2, left: form.eco_mode ? 18 : 2, width: 16, height: 16, background: '#111', borderRadius: '50%', transition: 'left 0.2s' }} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                Delay Probability (re-routing trigger): {(form.delay_probability * 100).toFixed(0)}%
              </label>
              <input type="range" min="0" max="1" step="0.05"
                value={form.delay_probability}
                onChange={e => set('delay_probability', e.target.value)}
                style={{ width: '100%', accentColor: 'var(--accent-blue)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
                <span>0%</span>
                <span style={{ color: form.delay_probability > 0.6 ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                  {form.delay_probability > 0.6 ? '⚡ Re-routing active' : '— Triggers at 60%+'}
                </span>
                <span>100%</span>
              </div>
            </div>

            {error && (
              <div className="alert alert-red" style={{ marginBottom: 16 }}>
                <span>⚠️</span>{error}
              </div>
            )}

            <button type="submit" className="btn btn-primary" disabled={loading}
              style={{ width: '100%', justifyContent: 'center', padding: '12px' }}>
              {loading
                ? <><div className="spinner" style={{ width: 16, height: 16 }} />Optimizing…</>
                : '🚀 Optimize Route'}
            </button>
          </form>
        </div>

        {/* Results panel */}
        <div>
          {result ? (
            <div className="card fade-in">
              <div className="section-title">
                <h3>📍 Route Results</h3>
                <div className="flex gap-8">
                  {[['primary','Primary','badge-blue'],['alt1','Alt-1','badge-amber'],['alt2','Alt-2','badge-purple']].map(([k,l,cls]) => (
                    <button key={k} className={`badge ${selected === k ? cls : 'badge-muted'}`}
                      style={{ cursor: 'pointer' }} onClick={() => setSelected(k)}>{l}</button>
                  ))}
                </div>
              </div>

              {activeRoute && (
                <>
                  <div className="route-metrics-row">
                    <div className="route-metric">
                      <div className="route-metric-value text-blue font-mono">
                        {activeRoute.total_distance_km?.toFixed(0)} km
                      </div>
                      <div className="route-metric-label">Distance</div>
                    </div>
                    <div className="route-metric">
                      <div className="route-metric-value text-green font-mono">
                        {activeRoute.total_time_h?.toFixed(2)} h
                      </div>
                      <div className="route-metric-label">Est. Time</div>
                    </div>
                    <div className="route-metric">
                      <div className="route-metric-value text-amber font-mono">
                        ₹{activeRoute.estimated_cost?.toFixed(0)}
                      </div>
                      <div className="route-metric-label">Est. Cost</div>
                    </div>
                  </div>

                  <div className="waypoint-list">
                    {activeRoute.waypoints?.map((w, i) => (
                      <div key={i} className="waypoint-item">
                        <div className={`waypoint-dot ${i === 0 ? 'waypoint-first' : i === activeRoute.waypoints.length-1 ? 'waypoint-last' : 'waypoint-mid'}`}>
                          {i === 0 ? 'A' : i === activeRoute.waypoints.length-1 ? 'B' : i}
                        </div>
                        <div>
                          <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{w.city}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                            {w.lat?.toFixed(4)}°N, {w.lon?.toFixed(4)}°E
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {result.efficiency_vs_baseline && (
                    <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                      <div className="badge badge-green">⚡ Time saving: {result.efficiency_vs_baseline.time_saving_pct}%</div>
                      <div className="badge badge-blue">📏 Distance saving: {result.efficiency_vs_baseline.distance_saving_pct}%</div>
                      {form.eco_mode && <div className="badge" style={{ background: 'rgba(0,255,136,0.15)', color: '#00ff88' }}>🍃 CO2 Saved: {((result?.alternatives?.[0]?.total_distance_km || activeRoute.total_distance_km) - activeRoute.total_distance_km * 0.15).toFixed(1)} kg</div>}
                      {result.rerouted_due_to_anomaly && <div className="badge badge-red">↺ Re-routed</div>}
                      {avoidBbox && <div className="badge badge-amber">🛡️ SLA Geofence Active</div>}
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 260 }}>
              <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: 10, opacity: 0.3 }}>🗺️</div>
                <div>Select parameters and click Optimize Route</div>
                <div style={{ fontSize: '0.8rem', marginTop: 8 }}>Routes will draw on the Mapbox map above</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
