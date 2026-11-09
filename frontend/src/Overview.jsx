import { useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import { api, LEVELS, fmtDate } from './api.js'

export default function Overview({ role, date, setDate, onOpen }) {
  const [meta, setMeta] = useState(null)
  const [areas, setAreas] = useState([])
  const [alerts, setAlerts] = useState(null)  // null = still loading
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [risk, setRisk] = useState([])
  const [notes, setNotes] = useState([])
  const [playing, setPlaying] = useState(false)
  const timer = useRef()

  useEffect(() => { api('meta').then(setMeta).catch(() => setFailed(true)) }, [attempt])
  useEffect(() => {
    let current = true  // ignore late answers for a role the user has already switched away from
    setAreas([]); setAlerts(null); setRisk([]); setNotes([]); setFailed(false)
    const fail = () => current && setFailed(true)
    api('areas', { role }).then(d => current && setAreas(d)).catch(fail)
    api('alerts', { role }).then(d => current && setAlerts(d)).catch(fail)
    return () => { current = false }
  }, [role, attempt])
  useEffect(() => {
    let current = true
    api('risk', { date, role }).then(d => current && setRisk(d)).catch(() => { if (current) { setRisk([]); setFailed(true) } })
    if (role === 'public') setNotes([])
    else api('notifications', { date, role }).then(d => current && setNotes(d)).catch(() => current && setNotes([]))
    return () => { current = false }
  }, [date, role, attempt])

  const days = useMemo(() => {
    if (!meta) return []
    const out = []
    for (let d = new Date(meta.start + 'T00:00:00Z'); d <= new Date(meta.end + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1))
      out.push(d.toISOString().slice(0, 10))
    return out
  }, [meta])
  const idx = days.indexOf(date)

  useEffect(() => {
    if (!playing) return
    timer.current = setInterval(() => setDate(d => {
      const i = days.indexOf(d)
      if (i >= days.length - 1) { setPlaying(false); return d }
      return days[i + 1]
    }), 250)
    return () => clearInterval(timer.current)
  }, [playing, days, setDate])

  const riskBy = Object.fromEntries(risk.map(r => [r.area_id, r]))
  const known = (alerts || []).filter(a => a.start <= date)
  const active = known.filter(a => a.end >= date)
  const latest = Object.fromEntries(known.map(a => [a.area_id, a]))  // known is in start order, so the last one wins
  const play = () => {
    if (!playing && idx >= days.length - 1) setDate(days[0])  // finished replay: start again from the first day
    setPlaying(p => !p)
  }

  return (
    <div className="overview">
      <section className="card map-card">
        <div className="card-head">
          <h2>Risk on {fmtDate(date)} 2025</h2>
          <Legend />
        </div>
        <MapContainer center={[25.15, 55.25]} zoom={10} scrollWheelZoom={false} className="map">
          {/* OSM's tile policy: use tile.openstreetmap.org (no a/b/c subdomains) and send a Referer */}
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} />
          {areas.map(a => {
            const r = riskBy[a.id]
            const lv = LEVELS[r?.level || 'normal']
            return (
              <CircleMarker key={a.id} center={[a.lat, a.lon]}
                radius={(a.type === 'site' ? 7 : 12) + Math.min(r?.risk || 0, 12) * 1.6}
                pathOptions={{ color: lv.color, fillColor: lv.color, fillOpacity: 0.35, weight: 2, dashArray: a.type === 'site' ? '4 3' : null }}
                eventHandlers={latest[a.id] ? { click: () => onOpen(latest[a.id]) } : {}}>
                <Tooltip>
                  <strong>{a.name}</strong> {a.type === 'site' ? '(work site)' : ''}<br />
                  {lv.label} · risk {r?.risk ?? '–'}
                  {latest[a.id] && <><br />Select to open its latest alert</>}
                  {r?.missing?.length ? <><br />Missing today: {r.missing.map(s => meta?.signals?.[s]?.label || s).join(', ')}</> : null}
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
        <div className="replay-controls">
          <div className="replay">
            <button className="btn primary" onClick={play} disabled={!days.length} aria-label={playing ? 'Pause replay' : 'Play replay'}>
              {playing ? 'Pause' : 'Play'}
            </button>
            <input type="range" min={0} max={Math.max(0, days.length - 1)} value={Math.max(0, idx)}
              onChange={e => setDate(days[+e.target.value])} aria-label="Replay date" />
            <span className="mono">{date}</span>
          </div>
          <div className="jumps">
            <span className="muted small">Jump to</span>
            {meta?.scenarios.map(s => (
              <button key={s.id} className="btn" onClick={() => { setPlaying(false); setDate(s.focus) }}>
                {s.short} · {fmtDate(s.focus)}
              </button>
            ))}
          </div>
        </div>
        <p className="muted small">Replay shows what was known on each day — every signal arrives after its reporting delay. Dashed circles are Gulf Build Co. work sites.</p>
      </section>

      <section className="card feed">
        <h2>Alerts <span className="muted">({active.length} active)</span></h2>
        {failed && (
          <div className="down" role="alert">
            <p>Couldn't load the data. The server may be waking up, which can take up to a minute.</p>
            <button className="btn" onClick={() => setAttempt(n => n + 1)}>Try again</button>
          </div>
        )}
        {!failed && alerts === null && <p className="muted">Loading alerts…</p>}
        {alerts && known.length === 0 && <p className="muted">No alerts raised up to this date. Press Play or drag the slider.</p>}
        {[...known].reverse().map(a => {
          const lv = LEVELS[a.level]
          const on = a.end >= date
          return (
            <button key={a.id} className={on ? 'alert-row on' : 'alert-row'} onClick={() => onOpen(a)}>
              <span className="pill" style={{ background: lv.color }}>{lv.label}</span>
              <span className="alert-main">
                <strong>{a.area}</strong>
                <span className="muted small">{fmtDate(a.start)} – {fmtDate(a.end)} · {a.category}{on ? ' · active' : ''}</span>
                <span className="small">{a.action}</span>
              </span>
            </button>
          )
        })}
        {role !== 'public' && (
          <>
            <h2 className="notes-head">Notifications sent <span className="muted">({notes.length})</span></h2>
            {notes.length === 0 && <p className="muted small">Each responsible role is notified the day an alert opens.</p>}
            <ul className="notes">
              {[...notes].reverse().map(n => (
                <li key={n.id}>
                  <span className="mono small">{fmtDate(n.date)}</span>
                  <span><strong>{n.to}</strong> · {n.area} <span className="muted">({LEVELS[n.level].label.toLowerCase()}, {n.category})</span></span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  )
}

function Legend() {
  return (
    <div className="legend">
      {Object.values(LEVELS).map(l => <span key={l.label}><i style={{ background: l.color }} />{l.label}</span>)}
    </div>
  )
}
