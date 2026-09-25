import React from 'react'
import styles from './EmptyState.module.css'

interface EmptyStateProps {
  title: string
  description: string
  illustration?: React.ReactNode
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({
  title,
  description,
  illustration,
  action,
}: EmptyStateProps) {
  return (
    <div className={styles.container}>
      <div className={styles.content}>
        {illustration && (
          <div className={styles.illustration} aria-hidden="true">
            {illustration}
          </div>
        )}
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.description}>{description}</p>
        {action && (
          <button
            type="button"
            className={styles.action}
            onClick={action.onClick}
          >
            {action.label}
          </button>
        )}
      </div>
    </div>
  )
}

export default EmptyState