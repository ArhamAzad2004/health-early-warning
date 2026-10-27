import { useEffect, useState } from 'react'
import { api, fmtDate } from './api.js'

const pct = v => (v == null ? '–' : `${Math.round(v * 100)}%`)
const CHOSEN = 4.5

export default function Validation({ role }) {
  const [b, setB] = useState(null)
  const [areas, setAreas] = useState([])
  useEffect(() => { api('backtest', { role }).then(setB) }, [role])
  useEffect(() => { api('areas', { role }).then(setAreas).catch(() => setAreas([])) }, [role])
  if (!b) return <p className="muted">Running back-test…</p>

  return (
    <div className="validation">
      <p className="muted">Replayed 1 May – 30 Sep 2025 day by day, using each signal only once it would have been reported. Two outbreaks were injected as ground truth.</p>
      <div className="tiles">
        <Tile label="Outbreaks detected" value={pct(b.sensitivity)} note={`${pct(b.area_sensitivity)} of affected areas`} />
        <Tile label="Mean lead time" value={`${b.mean_lead_time_days} days`} note="first alert → harm peak" />
        <Tile label="Precision (PPV)" value={pct(b.ppv)} note={`${b.total_alerts} alerts in 5 months`} />
        <Tile label="False alarms" value={b.false_alarms} note="across 11 areas" />
        <Tile label="Median data latency" value={`${b.median_latency_days} day`} note="per signal: see below" />
      </div>

      <section className="card">
        <h2>Scenarios</h2>
        <table>
          <thead><tr><th>Scenario</th><th>First alert</th><th>Harm peak</th><th>Lead time</th><th>Areas flagged</th></tr></thead>
          <tbody>{b.scenarios.map(s => (
            <tr key={s.id}>
              <td>{s.name}</td><td>{s.first_alert ? fmtDate(s.first_alert) : 'missed'}</td><td>{fmtDate(s.peak)}</td>
              <td className="mono">{s.lead_time_days ?? '–'} d</td><td>{s.areas_hit.length} of {s.areas_affected.length}</td>
            </tr>))}</tbody>
        </table>
        {b.scenarios.filter(s => s.missed_areas?.length).map(s => (
          <p key={s.id} className="muted small">Known limit — {s.name}: {s.missed_areas.map(id => areas.find(a => a.id === id)?.name || id).join(', ')} not alerted (accepted known limit: absence-only workplace signal could not corroborate on two consecutive days).</p>
        ))}
      </section>

      <div className="detail-grid">
        <section className="card">
          <h2>Calibration: picking the threshold</h2>
          <p className="muted small">Lower thresholds alert sooner but cry wolf. We chose {CHOSEN}: same detection, one false alarm.</p>
          <table>
            <thead><tr><th>Threshold</th><th>Detected</th><th>PPV</th><th>False alarms</th><th>Lead</th></tr></thead>
            <tbody>{b.calibration.map(c => (
              <tr key={c.threshold} className={c.threshold === CHOSEN ? 'chosen' : ''}>
                <td className="mono">{c.threshold}{c.threshold === CHOSEN ? ' ✓' : ''}</td><td>{pct(c.sensitivity)}</td><td>{pct(c.ppv)}</td>
                <td>{c.false_alarms}</td><td>{c.mean_lead_time_days ?? '–'} d</td>
              </tr>))}</tbody>
          </table>
        </section>
        <section className="card">
          <h2>When an input goes missing</h2>
          <p className="muted small">Re-run with one data feed switched off.</p>
          <table>
            <thead><tr><th>Without</th><th>Detected</th><th>PPV</th><th>False alarms</th><th>Lead</th></tr></thead>
            <tbody>
              <tr className="chosen"><td>All feeds</td><td>{pct(b.sensitivity)}</td><td>{pct(b.ppv)}</td><td>{b.false_alarms}</td><td>{b.mean_lead_time_days} d</td></tr>
              {b.missing_input.map(m => (
                <tr key={m.without}><td>{m.label}</td><td>{pct(m.sensitivity)}</td><td>{pct(m.ppv)}</td><td>{m.false_alarms}</td><td>{m.mean_lead_time_days ?? '–'} d</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <section className="card">
        <h2>Estimated impact at Gulf Build Co.</h2>
        <div className="tiles">
          <Tile label="Lost workdays avoided" value={b.impact.avoided_lost_workdays} note={`of ${b.impact.excess_absence_days} excess absence days`} />
          <Tile label="Incidents avoided" value={b.impact.avoided_incidents} note={`of ${b.impact.excess_incidents} excess incidents`} />
          <Tile label="High-severity avoided" value={b.impact.avoided_high_severity_incidents} note="estimate" />
        </div>
        <ul className="small muted">{b.impact.assumptions.map(a => <li key={a}>{a}</li>)}</ul>
      </section>
    </div>
  )
}

function Tile({ label, value, note }) {
  return (
    <div className="tile">
      <span className="muted small">{label}</span>
      <strong className="tile-value">{value}</strong>
      <span className="muted small">{note}</span>
    </div>
  )
}
