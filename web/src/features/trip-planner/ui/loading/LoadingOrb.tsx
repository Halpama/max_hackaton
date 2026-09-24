import { SparklesIcon } from '../shared/icons'
import styles from './LoadingOrb.module.css'

export function LoadingOrb() {
  return (
    <div className={styles.orb} aria-hidden>
      <span className={styles.ring} />
      <span className={styles.ringDelayed} />
      <span className={styles.sweep} />
      <span className={styles.core}>
        <SparklesIcon className={styles.icon} width={44} height={44} />
      </span>
    </div>
  )
}
