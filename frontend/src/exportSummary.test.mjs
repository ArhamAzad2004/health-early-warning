import test from 'node:test'
import assert from 'node:assert/strict'
import { summaryCsv } from './exportSummary.js'

const backtest = {
  sensitivity: 1, area_sensitivity: 0.8, ppv: 0.8, false_alarms: 1, total_alerts: 5, mean_lead_time_days: 4,
  median_latency_days: 1, impact: { avoided_lost_workdays: 51, avoided_incidents: 15, assumptions: ['30% prevented'] },
  scenarios: [{ name: 'Heat cluster', first_alert: '2025-07-18', peak: '2025-07-23', lead_time_days: 5, known_limit: null }],
}

test('quotes cells and escapes embedded quotes and commas', () => {
  const csv = summaryCsv(backtest, [{ area: 'Site "A", Jebel Ali', start: '2025-07-20', end: '2025-07-27',
    level: 'alert', category: 'heat', action: 'Enforce breaks', roles: ['HSE', 'Inspector'], confidence: 'medium' }])
  assert.match(csv, /"Site ""A"", Jebel Ali"/)
  assert.match(csv, /"HSE; Inspector"/)
})

test('neutralises spreadsheet formulas (CSV injection)', () => {
  const csv = summaryCsv(backtest, [{ area: '=HYPERLINK("http://evil")', action: '+cmd', start: '', end: '', level: '', category: '', roles: [], confidence: '' }])
  assert.ok(!csv.includes('"=HYPERLINK'))
  assert.match(csv, /"'=HYPERLINK\(""http:\/\/evil""\)"/)
  assert.match(csv, /"'\+cmd"/)
})
