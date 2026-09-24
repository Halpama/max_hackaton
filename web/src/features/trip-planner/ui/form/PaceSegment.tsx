import type { TripPace } from '../../model'
import { PACE_OPTIONS } from '../../model'
import styles from './PaceSegment.module.css'

interface PaceSegmentProps {
  value: TripPace
  onChange: (value: TripPace) => void
}

export function PaceSegment({ value, onChange }: PaceSegmentProps) {
  return (
    <div className={styles.track} role="tablist" aria-label="Темп поездки">
      {PACE_OPTIONS.map((option) => {
        const active = option.id === value
        return (
          <button
            key={option.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={active ? styles.itemActive : styles.item}
            onClick={() => onChange(option.id)}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
