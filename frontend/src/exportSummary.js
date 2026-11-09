// Regulator summary as CSV, built from data the API already returned (already aggregated and suppressed).

// Quote every cell; neutralise spreadsheet formulas (CSV injection) by prefixing a quote.
const cell = v => {
  let s = v == null ? '' : String(v)
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`
  return `"${s.replace(/"/g, '""')}"`
}
const rows = lines => lines.map(r => r.map(cell).join(',')).join('\r\n')

export function summaryCsv(b, alerts) {
  return rows([
    ['Sentinel Dubai summary', 'synthetic data, aggregated counts only'],
    [],
    ['Metric', 'Value'],
    ['Outbreaks detected', b.sensitivity], ['Affected areas flagged', b.area_sensitivity],
    ['Precision (PPV)', b.ppv], ['False alarms', b.false_alarms], ['Total alerts', b.total_alerts],
    ['Mean lead time (days)', b.mean_lead_time_days], ['Median data latency (days)', b.median_latency_days],
    ['Lost workdays avoided (estimate)', b.impact.avoided_lost_workdays],
    ['Incidents avoided (estimate)', b.impact.avoided_incidents],
    ...b.impact.assumptions.map(a => ['Assumption', a]),
    [],
    ['Scenario', 'First alert', 'Harm peak', 'Lead time (days)', 'Known limit'],
    ...b.scenarios.map(s => [s.name, s.first_alert, s.peak, s.lead_time_days, s.known_limit]),
    [],
    ['Area', 'Start', 'End', 'Level', 'Category', 'Recommended action', 'Responsible', 'Confidence'],
    ...alerts.map(a => [a.area, a.start, a.end, a.level, a.category, a.action, (a.roles || []).join('; '), a.confidence]),
  ])
}

export function downloadCsv(text, filename) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: filename })
  link.click()
  URL.revokeObjectURL(url)
}
