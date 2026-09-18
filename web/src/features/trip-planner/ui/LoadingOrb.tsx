import { SparklesIcon } from './icons'
import styles from './LoadingOrb.module.css'

export function LoadingOrb() {
  return (
    <div className={styles.orb} aria-hidden>
      <span className={styles.ring} />
      <span className={styles.ringDelayed} />
      <span className={styles.sweep} />
      <span className={styles.core}>
        <SparklesIcon />
      </span>
    </div>
  )
}
