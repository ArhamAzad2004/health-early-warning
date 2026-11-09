import { useEffect, useState } from 'react'
import { api, fmtDate } from './api.js'
import { downloadCsv, summaryCsv } from './exportSummary.js'

const pct = v => (v == null ? '–' : `${Math.round(v * 100)}%`)
const CHOSEN = 4.5
const small = v => v ?? '<5'  // the server hides impact totals that would be a 1-4 count

export default function Validation({ role, roleName }) {
  const [b, setB] = useState(null)
  const [areas, setAreas] = useState([])
  const [alerts, setAlerts] = useState(null)  // null = not loaded: export stays off
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let current = true  // ignore late answers for a previous role
    setB(null); setAlerts(null); setFailed(false)  // never export one role's back-test with another role's alerts
    const fail = () => current && setFailed(true)
    api('backtest', { role }).then(d => current && setB(d)).catch(fail)
    api('areas', { role }).then(d => current && setAreas(d)).catch(() => current && setAreas([]))
    api('alerts', { role }).then(d => current && setAlerts(d)).catch(fail)
    return () => { current = false }
  }, [role, attempt])
  if (failed) return (
    <div className="down" role="alert">
      <p>Couldn't load the back-test. The server may be waking up, which can take up to a minute.</p>
      <button className="btn" onClick={() => setAttempt(n => n + 1)}>Try again</button>
    </div>
  )
  if (!b) return <p className="muted">Running back-test…</p>

  return (
    <div className="validation">
      <div className="validation-head">
        <p className="muted">Replayed 1 May – 30 Sep 2025 day by day, using each signal only once it would have been reported. Two outbreaks were injected as ground truth.</p>
        <div className="export no-print">
          <button className="btn" disabled={!alerts} onClick={() => downloadCsv(summaryCsv(b, alerts, roleName), 'sentinel-summary-2025-05-01_2025-09-30.csv')}>Download CSV</button>
          <button className="btn" onClick={() => window.print()}>Print summary</button>
        </div>
      </div>
      <div className="tiles">
        <Tile label="Outbreaks detected" value={pct(b.sensitivity)} note={`${pct(b.area_sensitivity)} of affected areas`} />
        <Tile label="Mean lead time" value={`${b.mean_lead_time_days} days`} note="first alert → harm peak" />
        <Tile label="Precision (PPV)" value={pct(b.ppv)} note={`${b.total_alerts} alert${b.total_alerts === 1 ? '' : 's'} in 5 months`} />
        <Tile label="False alarms" value={b.false_alarms} note={`across ${areas.length || '–'} areas`} />
        <Tile label="Median data latency" value={`${b.median_latency_days} day${b.median_latency_days === 1 ? '' : 's'}`} note="per signal: see below" />
      </div>

      <section className="card">
        <h2>Scenarios</h2>
        <table>
            <caption className="sr-only">Scenarios: first alert, harm peak and lead time</caption>
          <thead><tr><th>Scenario</th><th>First alert</th><th>Harm peak</th><th>Lead time</th><th>Areas flagged</th></tr></thead>
          <tbody>{b.scenarios.map(s => (
            <tr key={s.id}>
              <td>{s.name}</td><td>{s.first_alert ? fmtDate(s.first_alert) : 'missed'}</td><td>{fmtDate(s.peak)}</td>
              <td className="mono">{s.lead_time_days == null ? '–' : `${s.lead_time_days} d`}</td><td>{s.areas_hit.length} of {s.areas_affected.length}</td>
            </tr>))}</tbody>
        </table>
        <p className="muted small">Lead time is the number of days between the first alert and the worst day; more is better.</p>
        {b.scenarios.filter(s => s.missed_areas?.length).map(s => (
          <p key={s.id} className="muted small">Known limit: {s.missed_areas.map(id => areas.find(a => a.id === id)?.name || id).join(', ')} not alerted in the {s.name.toLowerCase()}. {s.known_limit}</p>
        ))}
      </section>

      <div className="detail-grid">
        <section className="card">
          <h2>Calibration: picking the threshold</h2>
          <p className="muted small">Lower thresholds alert sooner but cry wolf. We chose {CHOSEN}: same detection, one false alarm.</p>
          <table>
            <caption className="sr-only">Alert threshold calibration</caption>
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
          <p className="muted small">Re-run with one data feed switched off. Compare each row with "All feeds" to see how much that feed matters.</p>
          <table>
            <caption className="sr-only">Detection with one data feed switched off</caption>
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
          <Tile label="Lost workdays avoided" value={small(b.impact.avoided_lost_workdays)} note={`of ${small(b.impact.excess_absence_days)} excess absence days`} />
          <Tile label="Incidents avoided" value={small(b.impact.avoided_incidents)} note={`of ${small(b.impact.excess_incidents)} excess incidents`} />
          <Tile label="High-severity avoided" value={small(b.impact.avoided_high_severity_incidents)} note="estimate" />
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
