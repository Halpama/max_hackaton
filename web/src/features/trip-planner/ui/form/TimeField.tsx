import { useEffect, useRef, useState } from 'react'
import styles from './TimeField.module.css'
import { ClockIcon } from '../shared/icons'

interface TimeFieldProps {
  label: string
  value: string
  min?: string
  max?: string
  onChange: (value: string) => void
}

function clampTime(value: string, min?: string, max?: string) {
  let next = value
  if (min && next < min) next = min
  if (max && next > max) next = max
  return next
}

/** Display HH:MM without letting Safari's native time chrome shift layout. */
function formatTime(value: string) {
  if (!/^\d{2}:\d{2}$/.test(value)) return value || '—:—'
  return value
}

export function TimeField({ label, value, min, max, onChange }: TimeFieldProps) {
  const [local, setLocal] = useState(value)
  const focusedRef = useRef(false)

  useEffect(() => {
    if (!focusedRef.current) setLocal(value)
  }, [value])

  const commit = (raw: string) => {
    if (!raw || !/^\d{2}:\d{2}$/.test(raw)) {
      setLocal(value)
      return
    }
    const next = clampTime(raw, min, max)
    setLocal(next)
    if (next !== value) onChange(next)
  }

  return (
    <label className={styles.trigger}>
      <span className={styles.icon} aria-hidden>
        <ClockIcon />
      </span>
      <span className={styles.copy}>
        <span className={styles.caption}>{label}</span>
        <span className={styles.value}>{formatTime(local)}</span>
      </span>
      <input
        className={styles.native}
        type="time"
        value={local}
        min={min}
        max={max}
        aria-label={label}
        onFocus={() => {
          focusedRef.current = true
        }}
        onChange={(event) => {
          const raw = event.target.value
          if (!raw) return
          // Keep edits local while the wheel is open — intermediate values
          // must not hit the 12h trip clamp until blur.
          setLocal(raw)
        }}
        onBlur={(event) => {
          focusedRef.current = false
          commit(event.target.value)
        }}
        onClick={(event) => {
          const input = event.currentTarget
          if (typeof input.showPicker !== 'function') return
          try {
            void input.showPicker()
          } catch {
            // Safari may reject showPicker — native interaction still works.
          }
        }}
      />
    </label>
  )
}
