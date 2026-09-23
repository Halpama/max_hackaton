import type { ReactNode } from 'react'
import styles from './StatusView.module.css'

interface StatusViewProps {
  tone?: 'neutral' | 'error'
  icon?: ReactNode
  title: string
  text?: string
  actionLabel?: string
  onAction?: () => void
  secondaryActionLabel?: string
  onSecondaryAction?: () => void
}

/** Centred empty / error state used while the backend has nothing to show yet. */
export function StatusView({
  tone = 'neutral',
  icon,
  title,
  text,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
}: StatusViewProps) {
  const hasPrimary = Boolean(actionLabel && onAction)
  const hasSecondary = Boolean(secondaryActionLabel && onSecondaryAction)

  return (
    <div className={styles.root} role="status">
      {icon ? (
        <span className={tone === 'error' ? styles.iconWarn : styles.icon}>{icon}</span>
      ) : null}
      <h2 className={styles.title}>{title}</h2>
      {text ? <p className={styles.text}>{text}</p> : null}
      {hasPrimary || hasSecondary ? (
        <div className={styles.actions}>
          {hasPrimary ? (
            <button type="button" className={styles.action} onClick={onAction}>
              {actionLabel}
            </button>
          ) : null}
          {hasSecondary ? (
            <button
              type="button"
              className={styles.actionSecondary}
              onClick={onSecondaryAction}
            >
              {secondaryActionLabel}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export function LoadingView({ title = 'Загружаем…' }: { title?: string }) {
  return (
    <div className={styles.root} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden />
      <p className={styles.text}>{title}</p>
    </div>
  )
}

export function ListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className={styles.skeletonList} aria-hidden>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className={styles.skeletonCard} />
      ))}
    </div>
  )
}
