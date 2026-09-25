import { useRef } from 'react'
import { formatShortDate } from '../../lib/format'
import { CalendarIcon } from '../shared/icons-sprite'
import styles from './DateField.module.css'

interface DateFieldProps {
  label: string
  value: string
  min?: string
  max?: string
  onChange: (value: string) => void
}

function clampDate(value: string, min?: string, max?: string) {
  let next = value
  if (min && next < min) next = min
  if (max && next > max) next = max
  return next
}

export function DateField({ label, value, min, max, onChange }: DateFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <label className={styles.trigger}>
      <span className={styles.icon} aria-hidden>
        <CalendarIcon />
      </span>
      <span className={styles.copy}>
        <span className={styles.caption}>{label}</span>
        <span className={styles.value}>{formatShortDate(value)}</span>
      </span>
      <input
        ref={inputRef}
        className={styles.native}
        type="date"
        value={value}
        min={min}
        max={max}
        aria-label={label}
        onChange={(event) => {
          const raw = event.target.value
          if (!raw) return
          onChange(clampDate(raw, min, max))
        }}
        onBlur={(event) => {
          const raw = event.target.value
          if (!raw) return
          const clamped = clampDate(raw, min, max)
          if (clamped !== raw) onChange(clamped)
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
