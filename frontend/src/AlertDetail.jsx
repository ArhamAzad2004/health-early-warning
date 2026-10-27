import { useEffect, useState } from 'react'
import { ComposedChart, Line, Area, XAxis, YAxis, Tooltip, ReferenceArea, ReferenceLine, ResponsiveContainer } from 'recharts'
import { api, LEVELS, fmtDate } from './api.js'

export default function AlertDetail({ role, alert, onBack }) {
  const [sig, setSig] = useState(null)
  const [meta, setMeta] = useState(null)
  useEffect(() => { api('signals', { area_id: alert.area_id, role }).then(setSig).catch(() => setSig(null)) }, [alert, role])
  useEffect(() => { api('meta').then(setMeta) }, [])

  const lv = LEVELS[alert.level]
  // Zoom the charts to three weeks either side of the alert.
  const from = shift(alert.start, -21), to = shift(alert.end, 14)
  const inView = rows => rows.filter(r => r.date >= from && r.date <= to)
  const top = Object.entries(alert.contributions || {}).slice(0, 4).map(([s]) => s)

  return (
    <div className="detail">
      <button className="btn ghost" onClick={onBack}>← Back to overview</button>
      <div className="detail-head">
        <span className="pill big" style={{ background: lv.color }}>{lv.label}</span>
        <div>
          <h1>{alert.area}</h1>
          <p className="muted">{alert.category} signal · {fmtDate(alert.start)} – {fmtDate(alert.end)} 2025
            {alert.peak_risk != null && <> · peak risk {alert.peak_risk}</>}</p>
        </div>
      </div>

      <div className="detail-grid">
        <section className="card action">
          <h2>Recommended action</h2>
          <p className="action-text">{alert.action}</p>
          {alert.roles && <>
            <h3>Responsible</h3>
            <ul>{alert.roles.map(r => <li key={r}>{r}</li>)}</ul>
          </>}
          {alert.completeness != null && (
            <p className="small">Data completeness <strong>{Math.round(alert.completeness * 100)}%</strong> · confidence <strong>{alert.confidence}</strong></p>
          )}
        </section>

        {alert.contributions && (
          <section className="card">
            <h2>Why: what drove the risk</h2>
            <div className="bars">
              {Object.entries(alert.contributions).filter(([, v]) => v > 0.01).map(([s, v]) => (
                <div key={s} className="bar-row">
                  <span className="bar-label">{meta?.signals[s]?.label || s}</span>
                  <span className="bar-track"><span className="bar" style={{ width: `${v * 100}%` }} /></span>
                  <span className="mono small">{Math.round(v * 100)}%</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {sig && (
        <section className="card">
          <h2>Fused risk score over time</h2>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={inView(sig.risk)} margin={{ left: 0, right: 16, top: 8 }}>
              <XAxis dataKey="date" tickFormatter={fmtDate} fontSize={12} minTickGap={24} />
              <YAxis fontSize={12} width={32} />
              <Tooltip labelFormatter={fmtDate} />
              <ReferenceArea x1={alert.start} x2={alert.end} fill={lv.color} fillOpacity={0.12} />
              {meta && Object.entries(meta.levels).map(([k, v]) => (
                <ReferenceLine key={k} y={v} stroke={LEVELS[k].color} strokeDasharray="4 3" label={{ value: LEVELS[k].label, fontSize: 11, position: 'right' }} />
              ))}
              <Line dataKey="risk" stroke="#1B1F24" dot={false} strokeWidth={2} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </section>
      )}

      {sig && (
        <section className="card">
          <h2>Signals vs their own baseline</h2>
          <div className="multiples">
            {(top.length ? top : Object.keys(sig.signals)).filter(s => sig.signals[s]).map(s => (
              <div key={s}>
                <h3>{meta?.signals[s]?.label || s} <span className="muted small">· reported after {meta?.signals[s]?.latency ?? '?'} d</span></h3>
                <ResponsiveContainer width="100%" height={130}>
                  <ComposedChart data={inView(sig.signals[s])} margin={{ left: 0, right: 8, top: 4 }}>
                    <XAxis dataKey="date" tickFormatter={fmtDate} fontSize={11} minTickGap={30} />
                    <YAxis fontSize={11} width={32} />
                    <Tooltip labelFormatter={fmtDate} formatter={(v, n) => [v ?? 'missing / <5', n]} />
                    <ReferenceArea x1={alert.start} x2={alert.end} fill={lv.color} fillOpacity={0.12} />
                    <Area dataKey="baseline" stroke="none" fill="#E1E4E8" isAnimationActive={false} name="baseline" />
                    <Line dataKey="value" stroke="#2457C5" dot={false} connectNulls={false} strokeWidth={1.8} isAnimationActive={false} name="observed" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
          <p className="muted small">Grey area = 28-day baseline. Gaps = missing data or suppressed small counts (&lt;5).</p>
        </section>
      )}

      {alert.evidence && (
        <div className="detail-grid">
          <section className="card">
            <h2>Evidence</h2>
            <table>
              <thead><tr><th>Signal</th><th>Day</th><th>Observed</th><th>Baseline</th><th>z</th></tr></thead>
              <tbody>
                {alert.evidence.map(e => (
                  <tr key={e.signal}>
                    <td>{e.label}</td><td>{fmtDate(e.date)}</td>
                    <td className="mono">{e.value ?? '<5'}</td>
                    <td className="mono">{e.baseline}</td><td className="mono">{e.z}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="card">
            <h2>Assumptions</h2>
            <ul className="small">{alert.assumptions.map(a => <li key={a}>{a}</li>)}</ul>
          </section>
        </div>
      )}
      {!alert.evidence && <p className="muted">Public view shows the advisory only. Evidence is visible to public-health and employer roles.</p>}
    </div>
  )
}

function shift(iso, days) {
  const d = new Date(iso + 'T00:00:00Z')
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}
