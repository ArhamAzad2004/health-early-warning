import { useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import { api, LEVELS, fmtDate } from './api.js'

export default function Overview({ role, date, setDate, onOpen }) {
  const [meta, setMeta] = useState(null)
  const [areas, setAreas] = useState([])
  const [alerts, setAlerts] = useState([])
  const [risk, setRisk] = useState([])
  const [playing, setPlaying] = useState(false)
  const timer = useRef()

  useEffect(() => { api('meta').then(setMeta) }, [])
  useEffect(() => {
    api('areas', { role }).then(setAreas)
    api('alerts', { role }).then(setAlerts)
  }, [role])
  useEffect(() => { api('risk', { date, role }).then(setRisk) }, [date, role])

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
  const known = alerts.filter(a => a.start <= date)
  const active = known.filter(a => a.end >= date)

  return (
    <div className="overview">
      <section className="card map-card">
        <div className="card-head">
          <h2>Risk on {fmtDate(date)} 2025</h2>
          <Legend />
        </div>
        <MapContainer center={[25.15, 55.25]} zoom={10} scrollWheelZoom={false} className="map">
          <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {areas.map(a => {
            const r = riskBy[a.id]
            const lv = LEVELS[r?.level || 'normal']
            return (
              <CircleMarker key={a.id} center={[a.lat, a.lon]}
                radius={(a.type === 'site' ? 7 : 12) + Math.min(r?.risk || 0, 12) * 1.6}
                pathOptions={{ color: lv.color, fillColor: lv.color, fillOpacity: 0.35, weight: 2, dashArray: a.type === 'site' ? '4 3' : null }}
                eventHandlers={{ click: () => { const al = known.filter(x => x.area_id === a.id).at(-1); if (al) onOpen(al) } }}>
                <Tooltip>
                  <strong>{a.name}</strong> {a.type === 'site' ? '(work site)' : ''}<br />
                  {lv.label} · risk {r?.risk ?? '–'}
                  {r?.missing?.length ? <><br />Missing today: {r.missing.join(', ')}</> : null}
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
        <div className="replay">
          <button className="btn" onClick={() => setPlaying(p => !p)} aria-label={playing ? 'Pause replay' : 'Play replay'}>
            {playing ? 'Pause' : 'Play'}
          </button>
          <input type="range" min={0} max={Math.max(0, days.length - 1)} value={Math.max(0, idx)}
            onChange={e => setDate(days[+e.target.value])} aria-label="Replay date" />
          <span className="mono">{date}</span>
        </div>
        <p className="muted small">Replay shows what was known on each day — every signal arrives after its reporting delay. Dashed circles are Gulf Build Co. work sites.</p>
      </section>

      <section className="card feed">
        <h2>Alerts <span className="muted">({active.length} active)</span></h2>
        {known.length === 0 && <p className="muted">No alerts raised up to this date. Press Play or drag the slider.</p>}
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
