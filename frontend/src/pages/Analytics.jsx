import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const COLORS = ['#00d4ff', '#00ff88', '#ffaa00', '#ff4466', '#a855f7', '#22d3ee']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#0d1117', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      {label && <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color || p.fill }} />
          <span style={{ color: '#8b9ab5' }}>{p.name}:</span>
          <span style={{ color: '#f0f4ff', fontWeight: 600 }}>{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</span>
        </div>
      ))}
    </div>
  )
}

// Generate demo chart data
function genEtaAccuracy() {
  return Array.from({ length: 12 }, (_, i) => ({
    month: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i],
    accuracy: 75 + Math.random() * 20,
    on_time: 65 + Math.random() * 25,
  }))
}

function genDelayTrend() {
  return Array.from({ length: 30 }, (_, i) => ({
    day: `D${i+1}`,
    delay_pct: 10 + Math.sin(i * 0.3) * 8 + Math.random() * 6,
    weather_impact: 5 + Math.random() * 10,
    traffic_impact: 3 + Math.random() * 8,
  }))
}

function genCargoPie(analyticsData) {
  if (analyticsData?.by_cargo_type) {
    return Object.entries(analyticsData.by_cargo_type).map(([name, value]) => ({ name, value }))
  }
  return [
    { name: 'General',     value: 35 },
    { name: 'Electronics', value: 22 },
    { name: 'Perishable',  value: 18 },
    { name: 'Hazardous',   value: 10 },
    { name: 'Fragile',     value: 8  },
    { name: 'Bulk',        value: 7  },
  ]
}

function genRouteEfficiency() {
  const routes = ['Mumbai→Delhi','Delhi→Blr','Hyd→Chennai','Mumbai→Pune','Kolkata→Bhu']
  return routes.map(r => ({
    route: r,
    baseline_time: 20 + Math.random() * 15,
    optimized_time: 15 + Math.random() * 10,
    saving_pct: 10 + Math.random() * 20,
  }))
}

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null)
  const [metrics,   setMetrics]   = useState(null)
  const [loading,   setLoading]   = useState(true)

  const etaData     = genEtaAccuracy()
  const delayData   = genDelayTrend()
  const routeData   = genRouteEfficiency()

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [a, m] = await Promise.all([
          axios.get('/api/analytics'),
          axios.get('/api/predict/metrics'),
        ])
        setAnalytics(a.data)
        setMetrics(m.data)
      } catch {}
      setLoading(false)
    }
    fetchData()
    const id = setInterval(fetchData, 15000)
    return () => clearInterval(id)
  }, [])

  const cargoData = genCargoPie(analytics)

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>📊 Analytics</h1>
        <p>Historical performance metrics, model accuracy scores, delay trend analysis, and route efficiency comparisons</p>
      </div>

      {/* Model Metrics Cards */}
      <div className="kpi-grid" style={{ marginBottom: 32 }}>
        <div className="kpi-card blue">
          <div className="kpi-icon">🧠</div>
          <div className="kpi-label">ETA Model MAE</div>
          <div className="kpi-value blue font-mono">
            {metrics?.eta?.mae_hours != null ? `${metrics.eta.mae_hours.toFixed(2)}h` : '—'}
          </div>
          <div className="kpi-sub">R² = {metrics?.eta?.r2?.toFixed(4) ?? '—'}</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-icon">⚠️</div>
          <div className="kpi-label">Delay AUC-ROC</div>
          <div className="kpi-value green font-mono">
            {metrics?.delay?.auc_roc != null ? (metrics.delay.auc_roc * 100).toFixed(1) + '%' : '—'}
          </div>
          <div className="kpi-sub">Random Forest Classifier</div>
        </div>
        <div className="kpi-card amber">
          <div className="kpi-icon">💰</div>
          <div className="kpi-label">Cost Model MAE</div>
          <div className="kpi-value amber font-mono">
            {metrics?.cost?.mae != null ? `₹${metrics.cost.mae.toFixed(1)}` : '—'}
          </div>
          <div className="kpi-sub">R² = {metrics?.cost?.r2?.toFixed(4) ?? '—'}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon">📦</div>
          <div className="kpi-label">Total Shipments</div>
          <div className="kpi-value text-purple">{analytics?.total_shipments ?? '—'}</div>
          <div className="kpi-sub">On-time: {analytics?.on_time_rate_pct ?? '—'}%</div>
        </div>
      </div>

      {loading && <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>Loading analytics…</div>}

      {/* Charts row 1 */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* ETA Accuracy Area Chart */}
        <div className="card">
          <div className="section-title"><h3>📈 ETA Model Accuracy (12 Months)</h3></div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={etaData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00ff88" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="month" tick={{ fill: '#4a5568', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} axisLine={false} tickLine={false} domain={[60, 100]} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="accuracy" stroke="#00d4ff" strokeWidth={2} fill="url(#blueGrad)" name="Accuracy %" />
              <Area type="monotone" dataKey="on_time"  stroke="#00ff88" strokeWidth={2} fill="url(#greenGrad)" name="On-time %" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Cargo Type Pie */}
        <div className="card">
          <div className="section-title"><h3>🎯 Shipment Mix by Cargo Type</h3></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <ResponsiveContainer width="50%" height={200}>
              <PieChart>
                <Pie data={cargoData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                  {cargoData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {cargoData.map((d, i) => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.78rem' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                  <span style={{ color: 'var(--text-secondary)', flex: 1 }}>{d.name}</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Delay Trend */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="section-title"><h3>⚠️ Delay Trend Analysis (30 Days)</h3></div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={delayData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="delGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ff4466" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ff4466" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="wGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ffaa00" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#ffaa00" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="day" tick={{ fill: '#4a5568', fontSize: 10 }} axisLine={false} tickLine={false} interval={4} />
            <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '0.78rem', color: '#8b9ab5' }} />
            <Area type="monotone" dataKey="delay_pct"      name="Overall Delay %"     stroke="#ff4466" strokeWidth={2} fill="url(#delGrad)" />
            <Area type="monotone" dataKey="weather_impact" name="Weather Impact %"     stroke="#ffaa00" strokeWidth={1.5} fill="url(#wGrad)" />
            <Area type="monotone" dataKey="traffic_impact" name="Traffic Impact %"     stroke="#a855f7" strokeWidth={1.5} fill="none" strokeDasharray="4 3" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Route Efficiency Bar Chart */}
      <div className="card">
        <div className="section-title"><h3>🗺️ Route Optimization Efficiency</h3></div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={routeData} margin={{ top: 5, right: 10, left: -20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="route" tick={{ fill: '#4a5568', fontSize: 10 }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" />
            <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '0.78rem', color: '#8b9ab5' }} />
            <Bar dataKey="baseline_time"   name="Baseline Time (h)"   fill="rgba(139,154,181,0.3)" radius={[4,4,0,0]} />
            <Bar dataKey="optimized_time"  name="Optimized Time (h)"  fill="#00d4ff" radius={[4,4,0,0]}
              label={{ position: 'top', fill: '#00d4ff', fontSize: 10, formatter: v => `${v.toFixed(1)}h` }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
