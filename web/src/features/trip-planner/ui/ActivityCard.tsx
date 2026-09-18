import type { Activity } from '../model'
import styles from './ActivityCard.module.css'

interface ActivityCardProps {
  activity: Activity
  onClick?: () => void
}

export function ActivityCard({ activity, onClick }: ActivityCardProps) {
  return (
    <button type="button" className={styles.card} onClick={onClick}>
      <div className={styles.timeCol}>
        <p className={styles.time}>{activity.time}</p>
        <p className={styles.duration}>{activity.durationLabel}</p>
      </div>
      <div className={styles.copy}>
        <p className={styles.title}>{activity.title}</p>
        <p className={styles.meta}>{activity.meta}</p>
      </div>
      <span className={styles.chevron} aria-hidden>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M6 3l5 5-5 5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    </button>
  )
}
