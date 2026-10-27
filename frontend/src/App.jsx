import { useEffect, useState } from 'react'
import { api } from './api.js'
import Overview from './Overview.jsx'
import AlertDetail from './AlertDetail.jsx'
import Validation from './Validation.jsx'
import Privacy from './Privacy.jsx'

const ROLES = {
  public_health: 'District Public Health Officer',
  employer_hse: 'Gulf Build Co. HSE Manager',
  public: 'Public',
}

export default function App() {
  const [role, setRole] = useState('public_health')
  const [page, setPage] = useState('overview')
  const [alert, setAlert] = useState(null)
  const [date, setDate] = useState('2025-07-20')
  const [live, setLive] = useState(null)

  useEffect(() => { api('live').then(setLive).catch(() => setLive({ ok: false })) }, [])
  useEffect(() => { setAlert(null); if (page === 'alert') setPage('overview') }, [role])

  const open = a => { setAlert(a); setPage('alert') }
  const tabs = [['overview', 'Overview'], ['validation', 'Validation'], ['privacy', 'Privacy & governance']]
    .filter(([id]) => !(role === 'public' && id === 'validation'))

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <strong>Sentinel Dubai</strong>
          <span className="muted">Population &amp; workforce health early warning</span>
        </div>
        <nav>
          {tabs.map(([id, label]) => (
            <button key={id} className={page === id ? 'tab on' : 'tab'} onClick={() => setPage(id)}>{label}</button>
          ))}
        </nav>
        <label className="role">
          Viewing as
          <select value={role} onChange={e => setRole(e.target.value)}>
            {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </header>

      <div className="banner" role="note">
        Aggregated counts only · cells under 5 suppressed · <strong>not for individual employment or disciplinary use</strong>
        <span className="muted"> · Health and workforce data are simulated</span>
      </div>

      <LiveStrip live={live} />

      <main>
        {page === 'overview' && <Overview role={role} date={date} setDate={setDate} onOpen={open} />}
        {page === 'alert' && alert && <AlertDetail role={role} alert={alert} onBack={() => setPage('overview')} />}
        {page === 'validation' && <Validation role={role} />}
        {page === 'privacy' && <Privacy roles={ROLES} />}
      </main>
    </div>
  )
}

function LiveStrip({ live }) {
  if (!live) return <div className="live muted">Loading live Dubai conditions…</div>
  if (!live.ok) return <div className="live muted">Live Dubai conditions unavailable (offline) — the simulated replay still works.</div>
  return (
    <div className="live">
      <span className="live-dot" aria-hidden /> <strong>Live Dubai now</strong>
      <span>{live.temperature}°C (feels {live.feels_like}°C)</span>
      <span>Humidity {live.humidity}%</span>
      <span>PM10 {live.pm10} µg/m³</span>
      <span>US AQI {live.us_aqi}</span>
      <span className="muted">Open-Meteo · {live.time?.replace('T', ' ')}</span>
    </div>
  )
}
