import { Component, lazy, Suspense, useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import Overview from './Overview.jsx'
import Tour from './Tour.jsx'
import Validation from './Validation.jsx'
import Privacy from './Privacy.jsx'

const AlertDetail = lazy(() => import('./AlertDetail.jsx'))  // charts (Recharts) load only when an alert is opened
const TOUR_SEEN = 'sentinel-tour-seen'

const ROLES = {
  public_health: 'District Public Health Officer',
  employer_hse: 'Gulf Build Co. HSE Manager',
  public: 'Public',
}

const SCOPE = {
  public_health: 'all districts and work sites',
  employer_hse: 'Gulf Build Co. work sites only',
  public: 'districts only: weather, air quality and advisories',
}

export default function App() {
  const [role, setRole] = useState('public_health')
  const [page, setPage] = useState('overview')
  const [alert, setAlert] = useState(null)
  const [date, setDate] = useState('2025-07-20')
  const [live, setLive] = useState(null)
  const [notice, setNotice] = useState('')
  const [down, setDown] = useState(false)
  const [tour, setTour] = useState(false)
  const noticeTimer = useRef()

  useEffect(() => { try { if (!localStorage.getItem(TOUR_SEEN)) setTour(true) } catch { /* storage blocked: skip auto-start */ } }, [])
  const closeTour = () => { setTour(false); try { localStorage.setItem(TOUR_SEEN, '1') } catch { /* ignore */ } }
  const startTour = () => { setAlert(null); setPage('overview'); setTour(true) }

  const switchRole = r => {
    setRole(r)
    setNotice(`Now viewing as ${ROLES[r]}: ${SCOPE[r]}.`)
    clearTimeout(noticeTimer.current)
    noticeTimer.current = setTimeout(() => setNotice(''), 4000)
  }

  useEffect(() => { api('live').then(setLive).catch(() => setLive({ ok: false })) }, [])
  useEffect(() => { api('meta').catch(() => setDown(true)) }, [])
  useEffect(() => {
    setAlert(null)
    if (page === 'alert' || (role === 'public' && page === 'validation')) setPage('overview')
  }, [role])

  const open = a => { setAlert(a); setPage('alert'); history.pushState({ alert: a.id }, '') }
  // Browser Back from an alert returns to the overview instead of leaving the site.
  useEffect(() => {
    const back = () => setPage(p => (p === 'alert' ? 'overview' : p))
    addEventListener('popstate', back)
    return () => removeEventListener('popstate', back)
  }, [])
  const tabs = [['overview', 'Overview'], ['validation', 'Validation'], ['privacy', 'Privacy & governance']]
    .filter(([id]) => !(role === 'public' && id === 'validation'))

  return (
    <>
      <header className="topbar">
        <div className="top">
          <div className="brand">
            <strong>Sentinel Dubai</strong>
            <span>Population &amp; workforce health early warning</span>
          </div>
          <nav>
            {tabs.map(([id, label]) => (
              <button key={id} data-tour={id} className={page === id ? 'tab on' : 'tab'} aria-current={page === id ? 'page' : undefined} onClick={() => setPage(id)}>{label}</button>
            ))}
          </nav>
          <label className="role">
            Viewing as
            <select value={role} onChange={e => switchRole(e.target.value)}>
              {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
        </div>
      </header>

    <div className="shell">
      <div className="lede">
        <p>Replay summer 2025 in Dubai and watch alerts open days before heat and dust outbreaks peak.</p>
        <button className="btn" data-tour-start onClick={startTour}>Take the tour</button>
      </div>

      <p className="notice" role="status">{notice}</p>

      <div className="banner" role="note">
        Aggregated counts only · cells under 5 suppressed · <strong>not for individual employment or disciplinary use</strong>
        <span className="muted"> · Health and workforce data are simulated</span>
      </div>

      <LiveStrip live={live} />

      {down && (
        <p className="down" role="alert">Can't reach the data service. Running locally? Start it with <code>npm run dev</code> and reload.</p>
      )}

      <main>
        {page === 'overview' && <Overview role={role} date={date} setDate={setDate} onOpen={open} />}
        {page === 'alert' && alert && (
          <LoadGuard onBack={() => setPage('overview')}>
            <Suspense fallback={<p className="muted">Loading alert…</p>}>
              <AlertDetail role={role} alert={alert} onBack={() => setPage('overview')} />
            </Suspense>
          </LoadGuard>
        )}
        {page === 'validation' && <Validation role={role} roleName={ROLES[role]} />}
        {page === 'privacy' && <Privacy roles={ROLES} />}
      </main>

      <footer className="muted small">
        Independent portfolio project with simulated health data. Not affiliated with or endorsed by Dubai Health Authority.{' '}
        <a href="https://github.com/ArhamAzad2004/health-early-warning">Source on GitHub</a>
      </footer>
    </div>
    {tour && <Tour role={role} onClose={closeTour} />}
    </>
  )
}

// A failed chunk download (offline, or a new deploy replaced the file) must not blank the whole app.
class LoadGuard extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="down" role="alert">
        <p>This alert couldn't be loaded. Check your connection, then reload the page.</p>
        <button className="btn" onClick={() => location.reload()}>Reload page</button>{' '}
        <button className="btn" onClick={this.props.onBack}>Back to overview</button>
      </div>
    )
  }
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
