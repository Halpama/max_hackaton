import type { InterestId } from '../../model'
import { INTEREST_OPTIONS } from '../../model'
import styles from './InterestChips.module.css'

interface InterestChipsProps {
  value: InterestId[]
  onToggle: (id: InterestId) => void
}

export function InterestChips({ value, onToggle }: InterestChipsProps) {
  return (
    <div className={styles.wrap}>
      {INTEREST_OPTIONS.map((option) => {
        const active = value.includes(option.id)
        return (
          <button
            key={option.id}
            type="button"
            className={active ? styles.chipActive : styles.chip}
            onClick={() => onToggle(option.id)}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
