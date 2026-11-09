import { useEffect, useLayoutEffect, useRef, useState } from 'react'

const STEPS = [
  { target: '.map', title: 'The risk map', text: 'Each circle is a Dubai district, or a Gulf Build Co. work site if dashed. Colour shows the risk level and size grows with risk. Hover a circle for details.' },
  { target: '.replay-controls', title: 'Replay summer 2025', text: 'Press Play or drag the slider to see what the system knew on each day. The Jump to buttons go straight to the two test outbreaks.' },
  { target: '.feed', title: 'Alerts and what to do', text: 'An alert opens when two or more signals rise together for two days. Select one to see why it fired and who should act.' },
  { target: '.role', title: 'Who is looking', text: 'Switch roles. Health officers see everything, the employer sees only its own sites, and the public sees weather and advice only.' },
  { target: '[data-tour="validation"]', title: 'Proof it works', text: 'Validation shows how early and how accurately the system caught the test outbreaks, including the case it missed.' },
]
const CARD_W = 340
const GAP = 12

export default function Tour({ role, onClose }) {
  const [steps, setSteps] = useState(null)
  const [i, setI] = useState(0)
  const [box, setBox] = useState(null)
  const [cardH, setCardH] = useState(0)
  const card = useRef()
  const close = useRef(onClose)
  close.current = onClose

  // Recomputed on role change: the public role has no Validation tab.
  useLayoutEffect(() => {
    const found = STEPS.filter(s => document.querySelector(s.target))
    setSteps(found)
    setI(n => Math.min(n, found.length - 1))
  }, [role])
  useLayoutEffect(() => {
    const el = steps && document.querySelector(steps[i]?.target)
    if (!steps) return
    if (!el) { close.current(); return }  // target gone (e.g. the user changed tab): end the tour
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollIntoView({ block: 'center', behavior: still ? 'auto' : 'smooth' })
    const place = () => setBox(el.getBoundingClientRect())
    place()
    addEventListener('resize', place)
    addEventListener('scroll', place, true)
    return () => { removeEventListener('resize', place); removeEventListener('scroll', place, true) }
  }, [steps, i])
  useLayoutEffect(() => { if (card.current) setCardH(card.current.offsetHeight) })
  useEffect(() => { card.current?.focus() }, [i, steps, !!box])
  useEffect(() => {
    const before = document.activeElement
    const key = e => e.key === 'Escape' && close.current()
    addEventListener('keydown', key)
    return () => {
      removeEventListener('keydown', key)
      const back = before?.isConnected && before !== document.body ? before : document.querySelector('[data-tour-start]')
      back?.focus()
    }
  }, [])

  if (!steps?.length || !box) return null
  const step = steps[i]
  const last = i === steps.length - 1
  const width = Math.min(CARD_W, innerWidth - 2 * GAP)
  const h = cardH || 200
  let top = box.bottom + GAP                                        // below the target
  if (top + h > innerHeight - GAP) top = box.top - GAP - h          // else above it
  if (top < GAP) top = Math.max(GAP, innerHeight - h - GAP)         // else pinned to the bottom of the screen
  const style = { width, top, left: Math.min(Math.max(GAP, box.left), innerWidth - width - GAP) }

  return (
    <>
      <div className="tour-ring" aria-hidden style={{ top: box.top - 6, left: box.left - 6, width: box.width + 12, height: box.height + 12 }} />
      <div className="tour-card" role="dialog" aria-labelledby="tour-title" aria-describedby="tour-text" tabIndex={-1} ref={card} style={style}>
        <p className="tour-step">Step {i + 1} of {steps.length}</p>
        <h2 id="tour-title">{step.title}</h2>
        <p id="tour-text">{step.text}</p>
        <div className="tour-actions">
          <button className="btn ghost" onClick={onClose}>Skip tour</button>
          <span>
            {i > 0 && <button className="btn" onClick={() => setI(i - 1)}>Back</button>}
            <button className="btn primary" onClick={() => (last ? onClose() : setI(i + 1))}>{last ? 'Finish' : 'Next'}</button>
          </span>
        </div>
      </div>
    </>
  )
}
