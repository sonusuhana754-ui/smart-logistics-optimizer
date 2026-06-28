import { useState, useEffect } from 'react'
import axios from 'axios'

const API = "https://empowering-acceptance-a64b.up.railway.app";

const STATUS_BADGE = {
  pending:     'badge-amber',
  allocated:   'badge-blue',
  delivered:   'badge-green',
  unallocated: 'badge-red',
}

const PRIORITY_COLOR = {
  Critical: 'var(--accent-red)',
  High:     'var(--accent-amber)',
  Medium:   'var(--accent-blue)',
  Low:      'var(--text-muted)',
}

export default function ShipmentPlanner() {
  const [shipments,  setShipments]  = useState([])
  const [manifests,  setManifests]  = useState([])
  const [fleet,      setFleet]      = useState(null)
  const [loading,    setLoading]    = useState(false)
  const [allocating, setAllocating] = useState(false)
  const [lastReport, setLastReport] = useState(null)
  const [tab,        setTab]        = useState('shipments')
  const [addOpen,    setAddOpen]    = useState(false)
  const [addForm,    setAddForm]    = useState({ origin: 'Mumbai', destination: 'Delhi', cargo_type: 'General', priority: 'Medium', weight_kg: 500, distance_km: 1400 })

  const CITIES = ['Mumbai','Delhi','Bangalore','Chennai','Kolkata','Hyderabad','Pune','Ahmedabad','Jaipur','Lucknow']
  const CARGO  = ['General','Electronics','Perishable','Hazardous','Fragile','Bulk']
  const PRIO   = ['Low','Medium','High','Critical']

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [s, m, f] = await Promise.all([
        axios.get(`${API}/api/shipments`),
        axios.get(`${API}/api/manifests`),
        axios.get(`${API}/api/fleet`),
      ])
      setShipments(s.data.shipments || [])
      setManifests(m.data.manifests || [])
      setFleet(f.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchAll() }, [])

  const handleAutoAllocate = async () => {
    setAllocating(true)
    try {
      const { data } = await axios.post(`${API}/api/automate`)
      setLastReport(data)
      await fetchAll()
    } catch {}
    setAllocating(false)
  }

  const handleAddShipment = async (e) => {
    e.preventDefault()
    try {
      await axios.post(`${API}/api/shipments`, { ...addForm, weight_kg: Number(addForm.weight_kg), distance_km: Number(addForm.distance_km) })
      setAddOpen(false)
      await fetchAll()
    } catch {}
  }

  const setAdd = (k, v) => setAddForm(p => ({ ...p, [k]: v }))

  const pending   = shipments.filter(s => s.status === 'pending').length
  const allocated = shipments.filter(s => s.status === 'allocated').length
  const delivered = shipments.filter(s => s.status === 'delivered').length

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>📦 Shipment Planner</h1>
        <p>Automated vehicle allocation, priority-based scheduling, and real-time dispatch management</p>
      </div>

      {/* KPIs */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card amber">
          <div className="kpi-icon">⏳</div>
          <div className="kpi-label">Pending</div>
          <div className="kpi-value amber">{pending}</div>
          <div className="kpi-sub">awaiting allocation</div>
        </div>
        <div className="kpi-card blue">
          <div className="kpi-icon">🚛</div>
          <div className="kpi-label">In Transit</div>
          <div className="kpi-value blue">{allocated}</div>
          <div className="kpi-sub">dispatched vehicles</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-icon">✅</div>
          <div className="kpi-label">Delivered</div>
          <div className="kpi-value green">{delivered}</div>
          <div className="kpi-sub">completed orders</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon">🚗</div>
          <div className="kpi-label">Available Vehicles</div>
          <div className="kpi-value text-purple">{fleet?.available ?? '—'}</div>
          <div className="kpi-sub">of {fleet?.total_vehicles ?? '—'} total</div>
        </div>
      </div>

      {/* Automation Controls */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h3 style={{ marginBottom: 4 }}>⚙️ Automation Engine</h3>
            <p style={{ fontSize: '0.82rem', margin: 0 }}>
              Auto-allocates pending shipments to best-fit vehicles — sorted by priority, respecting weight constraints.
              Scheduler runs every 30s automatically.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
            <button className="btn btn-ghost" onClick={() => setAddOpen(o => !o)}>➕ Add Shipment</button>
            <button className="btn btn-primary" onClick={handleAutoAllocate} disabled={allocating || pending === 0}>
              {allocating ? <><div className="spinner" style={{ width: 16, height: 16 }} />Allocating…</> : '⚡ Auto-Allocate Now'}
            </button>
            <button className="btn btn-ghost" onClick={fetchAll} disabled={loading}>↺ Refresh</button>
          </div>
        </div>

        {addOpen && (
          <form onSubmit={handleAddShipment} style={{ marginTop: 20, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <div className="form-grid-3" style={{ marginBottom: 12 }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Origin</label>
                <select className="form-control" value={addForm.origin} onChange={e => setAdd('origin', e.target.value)}>
                  {CITIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Destination</label>
                <select className="form-control" value={addForm.destination} onChange={e => setAdd('destination', e.target.value)}>
                  {CITIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Cargo Type</label>
                <select className="form-control" value={addForm.cargo_type} onChange={e => setAdd('cargo_type', e.target.value)}>
                  {CARGO.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Priority</label>
                <select className="form-control" value={addForm.priority} onChange={e => setAdd('priority', e.target.value)}>
                  {PRIO.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Weight (kg)</label>
                <input type="number" className="form-control" value={addForm.weight_kg} onChange={e => setAdd('weight_kg', e.target.value)} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Distance (km)</label>
                <input type="number" className="form-control" value={addForm.distance_km} onChange={e => setAdd('distance_km', e.target.value)} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-success">✅ Add to Queue</button>
              <button type="button" className="btn btn-ghost" onClick={() => setAddOpen(false)}>Cancel</button>
            </div>
          </form>
        )}

        {lastReport && (
          <div className="alert alert-green" style={{ marginTop: 16 }}>
            <span>✅</span>
            <span>
              Allocation complete: <strong>{lastReport.allocated}</strong> shipments allocated,{' '}
              <strong>{lastReport.unallocated}</strong> unallocated. {lastReport.new_manifests?.length} dispatch manifests generated.
            </span>
          </div>
        )}

        {lastReport && lastReport.unallocated > 0 && fleet?.vehicles?.some(v => v.maintenance_flag) && (
          <div className="alert alert-amber" style={{ marginTop: 8 }}>
            <span>⚠️</span>
            <span>
              <strong>Risk Avoided:</strong> Critical shipments were blocked from allocation down to vehicles showing signs of impending maintenance needs. Reassigning or holding...
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {[['shipments','📦 Shipments'], ['manifests','📋 Manifests'], ['fleet','🚛 Fleet']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            style={{
              padding: '8px 18px', borderRadius: 8, cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600,
              border: '1px solid', transition: 'var(--transition)',
              borderColor: tab === k ? 'var(--accent-blue)' : 'var(--border)',
              background: tab === k ? 'rgba(0,212,255,0.08)' : 'transparent',
              color: tab === k ? 'var(--accent-blue)' : 'var(--text-secondary)',
            }}>
            {l}
          </button>
        ))}
      </div>

      {/* Shipments Table */}
      {tab === 'shipments' && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrapper">
            <table>
              <thead><tr>
                <th>ID</th><th>Route</th><th>Cargo</th><th>Priority</th><th>Weight</th><th>Vehicle</th><th>Status</th><th>Departure</th>
              </tr></thead>
              <tbody>
                {shipments.length === 0 && <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No shipments yet</td></tr>}
                {shipments.map(s => (
                  <tr key={s.shipment_id}>
                    <td><span className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--accent-blue)' }}>{s.shipment_id}</span></td>
                    <td>{s.origin} → {s.destination}</td>
                    <td>{s.cargo_type}</td>
                    <td><span style={{ color: PRIORITY_COLOR[s.priority], fontWeight: 700, fontSize: '0.8rem' }}>{s.priority}</span></td>
                    <td className="font-mono">{s.weight_kg?.toFixed(0)} kg</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontFamily: 'JetBrains Mono, monospace' }}>{s.vehicle_id ?? '—'}</td>
                    <td><span className={`badge ${STATUS_BADGE[s.status] ?? 'badge-muted'}`}>{s.status}</span></td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {s.estimated_departure ? new Date(s.estimated_departure).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Manifests Table */}
      {tab === 'manifests' && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrapper">
            <table>
              <thead><tr>
                <th>Manifest ID</th><th>Shipment</th><th>Vehicle</th><th>Route</th><th>Cargo</th><th>Weight</th><th>Departure</th>
              </tr></thead>
              <tbody>
                {manifests.length === 0 && <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No manifests yet — run Auto-Allocate</td></tr>}
                {manifests.map(m => (
                  <tr key={m.manifest_id}>
                    <td><span className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--accent-purple)' }}>{m.manifest_id}</span></td>
                    <td><span className="font-mono" style={{ fontSize: '0.78rem' }}>{m.shipment_id}</span></td>
                    <td><span className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--accent-blue)' }}>{m.vehicle_id}</span></td>
                    <td>{m.origin} → {m.destination}</td>
                    <td>{m.cargo_type}</td>
                    <td className="font-mono">{m.weight_kg?.toFixed(0)} kg</td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {m.estimated_departure ? new Date(m.estimated_departure).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Fleet Table */}
      {tab === 'fleet' && fleet && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrapper">
            <table>
              <thead><tr>
                <th>Vehicle ID</th><th>Type</th><th>Capacity</th><th>Load</th><th>Utilization</th><th>Location</th><th>Fleet Health</th><th>Status</th>
              </tr></thead>
              <tbody>
                {fleet.vehicles?.map(v => {
                  const util = (v.current_load_kg / v.capacity_kg) * 100
                  return (
                    <tr key={v.vehicle_id}>
                      <td><span className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--accent-blue)' }}>{v.vehicle_id}</span></td>
                      <td>{v.vehicle_type}</td>
                      <td className="font-mono">{v.capacity_kg.toLocaleString()} kg</td>
                      <td className="font-mono">{v.current_load_kg.toFixed(0)} kg</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div className="progress-bar-wrap" style={{ width: 60 }}>
                            <div className="progress-bar-fill" style={{ width: `${util}%`, background: util > 80 ? 'var(--accent-red)' : 'var(--accent-green)' }} />
                          </div>
                          <span style={{ fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace' }}>{util.toFixed(0)}%</span>
                        </div>
                      </td>
                      <td>
                        {v.maintenance_flag 
                          ? <span className="badge badge-amber">⚠️ Maintenance Recommended</span>
                          : <span className="badge badge-green">✨ Optimal</span>}
                      </td>
                      <td>
                        <span className={`badge ${v.status === 'Pre-positioned' ? 'badge-purple' : v.status === 'available' ? 'badge-green' : v.status === 'dispatched' ? 'badge-blue' : 'badge-muted'}`}>
                          {v.status}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
