import type { ReactNode } from 'react'
import styles from './trip.module.css'

interface ScreenProps {
  children: ReactNode
  flush?: boolean
  footer?: ReactNode
}

/** Content shell for MAX WebApp — native chrome (title/back/close) comes from the client. */
export function Screen({ children, flush, footer }: ScreenProps) {
  return (
    <div className={styles.screen}>
      <div className={`${styles.body} ${flush ? styles.bodyFlush : ''}`}>
        {children}
        {footer ? (
          <div className={`${styles.footer} ${flush ? styles.footerPadded : ''}`}>
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
