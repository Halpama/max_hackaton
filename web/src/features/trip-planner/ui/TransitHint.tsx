import type { TransitLeg } from '../model'
import styles from './TransitHint.module.css'

interface TransitHintProps {
  leg: TransitLeg
}

export function TransitHint({ leg }: TransitHintProps) {
  return (
    <div className={styles.hint}>
      <div className={styles.rail} aria-hidden>
        <span className={styles.line} />
        <span className={styles.mid}>
          {leg.mode === 'taxi' ? <CarIcon /> : <WalkIcon />}
        </span>
        <span className={styles.line} />
      </div>
      <div className={styles.copy}>
        <p className={styles.label}>{leg.label}</p>
      </div>
    </div>
  )
}

function WalkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="13.5" cy="5" r="2" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M8 21l2.2-6.2L7 12l3-4 3.2 2.4 2.3-1.2L18 11"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CarIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 11l2-4h10l2 4v6h-1.5a1.5 1.5 0 1 1-3 0h-5a1.5 1.5 0 1 1-3 0H5v-6z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  )
}
