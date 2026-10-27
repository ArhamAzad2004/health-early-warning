# Sentinel Dubai — Design Brief

## 1. Audience and tone

Public health officers, HSE managers and regulators who look at this screen between other tasks. They need to trust it in ten seconds and act in two minutes.

Tone: **calm operations console**. Trustworthy, quiet, precise. Numbers before decoration. Nothing flashes, pulses or shouts. Risk is shown with colour **and** words, never colour alone. The data is serious; the interface stays steady.

Reference feel: an air-traffic or utility control room, not a marketing dashboard and not a news ticker.

## 2. Global layout

- Fixed header (56 px): product name "Sentinel Dubai", nav (Overview · Validation · Privacy), role switcher (segmented control: Public health / Employer HSE / Public), and the date in view.
- Directly under the header, a thin persistent banner: "Aggregated surveillance data. Not for individual employment or disciplinary use." Muted background, always visible, never dismissable.
- Content area max-width 1440 px, 24 px gutters, 16 px grid gap. Desktop first; must still read at 1024 px.

## 3. Page layouts

### Overview
Two-column: left 60 % map, right 40 % stack.
- Left: Leaflet map (height = viewport − header − banner − slider). Date slider pinned under the map with play/pause and the current date in large type.
- Right, top to bottom: live environment strip (one row of small stat tiles: temperature, humidity, feels like, PM10, PM2.5, US AQI, dust), then the alert feed (scrollable list of alert cards).

### Alert detail
Single column, max 960 px.
1. Header block: area name, level chip with text, start–end, peak risk, completeness %, confidence.
2. Contribution shares (full width).
3. Multi-signal timeline: one small chart per signal stacked vertically, shared x-axis; the area's risk line with the three threshold lines (4.5 / 6.0 / 7.5) at the bottom.
4. Action card.
5. "Back to overview" link top and bottom.

### Validation
Single column: six metric tiles in a row → per-scenario table → missing-input table (5 rows) → calibration table (7 rows, 4.5 highlighted) → impact card with the assumption sentences beside the numbers.

### Privacy & governance
Short single-column text panel with headed sections; no charts.

## 4. Colour

Base: near-white background `#F7F8FA`, surface `#FFFFFF`, text `#1B1F24`, muted text `#5C6470`, borders `#E1E4E8`. One accent for interactive elements: `#2457C5`.

Risk levels (the API's `level` values) use the Okabe–Ito colour-blind-safe set, and every use carries the level word as text:

| Level | Colour | Hex | Text label |
|---|---|---|---|
| `normal` | grey | `#8C9196` | "Normal" |
| `watch` (≥ 4.5) | sky blue | `#56B4E9` | "Watch" |
| `warning` (≥ 6.0) | orange | `#E69F00` | "Warning" |
| `alert` (≥ 7.5) | vermillion | `#D55E00` | "Alert" |

Rules: never red/green pairs; never encode meaning in colour only; map circles get a 1.5 px dark outline so they read on tiles; signals in charts use distinct line styles (solid / dashed / dotted) as well as colour.

Dark mode is not required for the hackathon.

## 5. Typography

- UI font: Inter (or system sans). Sizes: 13 px body, 12 px table and labels, 15 px card titles, 20 px page titles, 28 px the single big number on metric tiles.
- Numbers: tabular figures (`font-variant-numeric: tabular-nums`) everywhere a column of numbers appears.
- No italics for emphasis; use weight 600.

## 6. Key components

**Alert card (feed)**: level chip (colour + word) · area name · start–end · top two contribution shares as small bars with percentages · completeness %. Whole card is clickable; focus ring visible.

**Contribution shares**: horizontal bars in the API's order (largest first), label left (signal plain label, e.g. "Heat/exertion incident reports"), percentage right. Signals missing for most of the window get a hollow bar with "limited data".

**Timeline chart**: observed line, baseline band (`baseline` ± floor) in light grey fill, alert window shaded in the level colour at 12 % opacity, `suppressed` points drawn as a small "<5" tick, `missing` days as gaps (not zero).

**Action card**: four stacked sections with labels: Action · Roles (responsible first, then notified) · Evidence (table: signal, date, observed, baseline, z, share) · Assumptions (bulleted). Completeness and confidence repeated at the top right. Category chip ("heat" / "respiratory").

**Map circle**: radius 8–28 px scaled by risk; fill = level colour at 70 %; tooltip "Al Quoz — Warning (risk 6.3)"; popup lists missing signals for that day.

**Live strip tile**: label, value, unit, "updated hh:mm" from `time`; when `ok` is false, a single tile reads "Live feed unavailable".

**Role switcher**: segmented control; changing it shows a brief toast "Viewing as Employer HSE — Gulf Build Co. sites only".

## 7. Accessibility

- Colour contrast ≥ 4.5:1 for text, ≥ 3:1 for chips and chart marks.
- Every level colour paired with its word; every chart has a text summary line under it ("Incident reports peaked at 9 vs baseline 2.1 on 20 Jul").
- Keyboard: slider operable with arrow keys; cards and circles focusable; visible focus ring.
- Map has a list fallback (the alert feed and risk table) so nothing is only on the map.
- `prefers-reduced-motion`: slider autoplay still works but no transitions on circle size.

## 8. Things to avoid

- Red/green status colours, blinking, pulsing badges, sirens, "CRITICAL" in caps.
- Gradients, glassmorphism, decorative 3D, hero sections.
- Colour-only legends; rainbow colour scales.
- Showing exact small counts (anything 1–4 is "<5").
- Any wording that implies an individual person ("a worker at Site A"); always "Site A".
- Causal words ("caused", "due to"). Use "rose alongside", "followed".
- Hiding assumptions behind a tooltip; they sit next to the numbers.
