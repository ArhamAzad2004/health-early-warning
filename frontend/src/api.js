export const api = (path, params = {}) =>
  fetch(`/api/${path}?${new URLSearchParams(params)}`).then(r => (r.ok ? r.json() : Promise.reject(r.status)))

export const LEVELS = {
  normal: { color: '#8C9196', label: 'No signal' },
  watch: { color: '#56B4E9', label: 'Watch' },
  warning: { color: '#E69F00', label: 'Warning' },
  alert: { color: '#D55E00', label: 'Alert' },
}

export const fmtDate = iso => new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
