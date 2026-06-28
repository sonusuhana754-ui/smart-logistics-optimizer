import { useState, useEffect } from 'react'
import axios from 'axios'
const API = import.meta.env.VITE_API_URL;
const CITIES    = ['Mumbai','Delhi','Bangalore','Chennai','Kolkata','Hyderabad','Pune','Ahmedabad','Jaipur','Lucknow','Surat','Kochi','Bhubaneswar','Coimbatore','Goa','Chandigarh','Nagpur','Indore','Bhopal','Visakhapatnam']
const CARGO     = ['General','Electronics','Perishable','Hazardous','Fragile','Bulk']
const PRIORITY  = ['Low','Medium','High','Critical']
const VEHICLES  = ['Van','Truck','Heavy Truck','Refrigerated','Flatbed']
const CARRIERS  = ['FastFreight','GlobalLogix','SwiftCargo','PrimeShip','EcoMove']

const RISK_COLOR = { Low: 'var(--accent-green)', Medium: 'var(--accent-amber)', High: 'var(--accent-amber)', Critical: 'var(--accent-red)' }
const RISK_BG    = { Low: 'rgba(0,255,136,0.08)', Medium: 'rgba(255,170,0,0.08)', High: 'rgba(255,170,0,0.08)', Critical: 'rgba(255,68,102,0.08)' }

function GaugeRing({ pct, color, label, size = 120 }) {
  const r = 44
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width={size} height={size} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dasharray 0.8s ease', filter: `drop-shadow(0 0 8px ${color})` }}
        />
        <text x="50" y="47" textAnchor="middle" fontSize="14" fontWeight="800" fill={color} fontFamily="Inter,sans-serif">{pct}%</text>
        <text x="50" y="61" textAnchor="middle" fontSize="8" fill="#4a5568" fontFamily="Inter,sans-serif">{label}</text>
      </svg>
    </div>
  )
}

export default function PredictionStudio() {
  const [form, setForm] = useState({
    origin: 'Mumbai', destination: 'Delhi', distance_km: 1400,
    cargo_type: 'General', priority: 'Medium', weight_kg: 500,
    vehicle_type: 'Truck', carrier: 'FastFreight',
  })
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState(null)
  const [rt, setRt]               = useState(null)
  const [history, setHistory]     = useState([])

  useEffect(() => {
    axios.get(`${API}/api/realtime`).then(r => setRt(r.data)).catch(() => {})
    const id = setInterval(() => axios.get(`${API}/api/realtime`).then(r => setRt(r.data)).catch(() => {}), 5000)
    return () => clearInterval(id)
  }, [])

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null); setResult(null)
    try {
      const { data } = await axios.post(`${API}/api/predict`, {
        ...form,
        distance_km: Number(form.distance_km),
        weight_kg: Number(form.weight_kg),
        departure_datetime: new Date().toISOString(),
      })
      setResult(data)
      setHistory(h => [{ ...data, id: Date.now(), label: `${form.origin} → ${form.destination}` }, ...h].slice(0, 5))
    } catch (err) {
      setError(err?.response?.data?.detail || 'Prediction failed — is the backend running?')
    } finally { setLoading(false) }
  }

  const delPct    = result?.delay_probability ?? 0
  const riskLevel = result?.delay_risk_level ?? 'Low'

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>🧠 Prediction Studio</h1>
        <p>AI-powered ETA forecasting, delay risk scoring, and cost estimation using XGBoost + Random Forest models</p>
      </div>

      {rt?.anomaly_active && (
        <div className="alert alert-red mb-24">
          <span>⚡</span>
          <span>Active anomaly detected — predictions adjusted with real-time multiplier for current conditions</span>
        </div>
      )}

      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Input Form */}
        <div className="card">
          <div className="section-title">
            <h3>📝 Shipment Details</h3>
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

            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Distance (km)</label>
                <input type="number" className="form-control" value={form.distance_km} min={50} max={5000} onChange={e => set('distance_km', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Weight (kg)</label>
                <input type="number" className="form-control" value={form.weight_kg} min={1} max={20000} onChange={e => set('weight_kg', e.target.value)} />
              </div>
            </div>

            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Cargo Type</label>
                <select className="form-control" value={form.cargo_type} onChange={e => set('cargo_type', e.target.value)}>
                  {CARGO.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Priority</label>
                <select className="form-control" value={form.priority} onChange={e => set('priority', e.target.value)}>
                  {PRIORITY.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>
            </div>

            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Vehicle Type</label>
                <select className="form-control" value={form.vehicle_type} onChange={e => set('vehicle_type', e.target.value)}>
                  {VEHICLES.map(v => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Carrier</label>
                <select className="form-control" value={form.carrier} onChange={e => set('carrier', e.target.value)}>
                  {CARRIERS.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
            </div>

            {error && <div className="alert alert-red" style={{ marginBottom: 16 }}><span>⚠️</span>{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', justifyContent: 'center', padding: '12px' }}>
              {loading ? <><div className="spinner" style={{ width: 16, height: 16 }} />Running Prediction…</> : '⚡ Run Prediction'}
            </button>
          </form>
        </div>

        {/* Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {result ? (
            <div className="card fade-in">
              <div className="section-title">
                <h3>📊 Prediction Results</h3>
                {result.rt_adjustment_applied && (
                  <span className="badge badge-amber">RT Adjusted ×{result.rt_multiplier}</span>
                )}
              </div>

              {/* Gauges */}
              <div style={{ display: 'flex', justifyContent: 'space-around', padding: '20px 0', borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
                <GaugeRing pct={Math.min(delPct, 100).toFixed(0)} color={RISK_COLOR[riskLevel]} label="Delay Risk" />
                <GaugeRing
                  pct={Math.min(Math.round((result.cost_factor / 500) * 100), 100)}
                  color="var(--accent-blue)" label="Cost Index"
                />
                <GaugeRing
                  pct={Math.min(Math.round((result.eta_hours / 50) * 100), 100)}
                  color="var(--accent-purple)" label="ETA Index"
                />
              </div>

              {/* 3-metric grid */}
              <div className="pred-result">
                <div className="pred-metric">
                  <div className="pred-metric-value text-blue font-mono">
                    {result.eta_hours?.toFixed(1)}h
                  </div>
                  <div className="pred-metric-label">ETA Duration</div>
                  <div className="pred-metric-sub">{new Date(result.predicted_eta).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</div>
                </div>
                <div className="pred-metric" style={{ background: RISK_BG[riskLevel] }}>
                  <div className="pred-metric-value" style={{ color: RISK_COLOR[riskLevel] }}>
                    {delPct.toFixed(1)}%
                  </div>
                  <div className="pred-metric-label">Delay Probability</div>
                  <div className="pred-metric-sub">
                    <span className={`badge badge-${riskLevel === 'Low' ? 'green' : riskLevel === 'Critical' ? 'red' : 'amber'}`}>
                      {riskLevel} Risk
                    </span>
                  </div>
                </div>
                <div className="pred-metric">
                  <div className="pred-metric-value text-green font-mono">
                    ₹{result.cost_factor?.toFixed(0)}
                  </div>
                  <div className="pred-metric-label">Cost Factor</div>
                  <div className="pred-metric-sub">estimated units</div>
                </div>
              </div>

              {/* Model info */}
              <div style={{ marginTop: 16, padding: 12, background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                  Active Conditions
                </div>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {[
                    { k: 'Weather', v: result.realtime_conditions?.weather_condition ?? '—' },
                    { k: 'Traffic', v: `${result.realtime_conditions?.traffic_density?.toFixed(0) ?? '—'}%` },
                    { k: 'Anomaly', v: result.realtime_conditions?.anomaly_active ? '⚡ Active' : 'None' },
                  ].map(({ k, v }) => (
                    <div key={k} style={{ fontSize: '0.78rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{k}: </span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 280, gap: 12 }}>
              <div style={{ fontSize: '3rem', opacity: 0.3 }}>🧠</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Fill in shipment details and run a prediction</div>
            </div>
          )}

          {/* Prediction History */}
          {history.length > 0 && (
            <div className="card">
              <div className="section-title"><h3>🕘 Recent Predictions</h3></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {history.map(h => (
                  <div key={h.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.8rem' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{h.label}</span>
                    <span style={{ color: 'var(--accent-blue)', fontFamily: 'JetBrains Mono, monospace' }}>{h.eta_hours?.toFixed(1)}h</span>
                    <span className={`badge badge-${h.delay_risk_level === 'Low' ? 'green' : h.delay_risk_level === 'Critical' ? 'red' : 'amber'}`}>
                      {h.delay_risk_level}
                    </span>
                    <span style={{ color: 'var(--accent-green)', fontFamily: 'JetBrains Mono, monospace' }}>₹{h.cost_factor?.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
