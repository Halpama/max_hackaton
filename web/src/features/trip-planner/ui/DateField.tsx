import { formatShortDate } from '../lib/format'
import { CalendarIcon } from './icons'
import styles from './DateField.module.css'

interface DateFieldProps {
  label: string
  value: string
  min?: string
  max?: string
  onChange: (value: string) => void
}

export function DateField({ label, value, min, max, onChange }: DateFieldProps) {
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
        className={styles.native}
        type="date"
        value={value}
        min={min}
        max={max}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
        onFocus={(event) => {
          const input = event.currentTarget
          if (typeof input.showPicker === 'function') {
            try {
              input.showPicker()
            } catch {
              // Desktop browsers may reject showPicker outside a direct gesture;
              // the native input itself remains clickable as fallback.
            }
          }
        }}
      />
    </label>
  )
}
