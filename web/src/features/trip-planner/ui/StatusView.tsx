import type { ReactNode } from 'react'
import styles from './StatusView.module.css'

interface StatusViewProps {
  tone?: 'neutral' | 'error'
  icon?: ReactNode
  title: string
  text?: string
  actionLabel?: string
  onAction?: () => void
}

/** Centred empty / error state used while the backend has nothing to show yet. */
export function StatusView({
  tone = 'neutral',
  icon,
  title,
  text,
  actionLabel,
  onAction,
}: StatusViewProps) {
  return (
    <div className={styles.root} role="status">
      {icon ? (
        <span className={tone === 'error' ? styles.iconWarn : styles.icon}>{icon}</span>
      ) : null}
      <h2 className={styles.title}>{title}</h2>
      {text ? <p className={styles.text}>{text}</p> : null}
      {actionLabel && onAction ? (
        <button type="button" className={styles.action} onClick={onAction}>
          {actionLabel}
        </button>
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
