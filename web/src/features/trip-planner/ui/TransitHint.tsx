import type { MouseEvent } from 'react'
import { yandexGoRouteUrl, yandexMapsRouteUrl } from '@/shared/lib/yandex'
import { getWebApp, isMaxWebApp } from '@/shared/lib/max'
import type { TransitLeg } from '../model'
import styles from './TransitHint.module.css'

interface TransitHintProps {
  leg: TransitLeg
  from: [number, number]
  to: [number, number]
}

function openExternal(event: MouseEvent<HTMLAnchorElement>, url: string) {
  // CDN max-web-app.js injects a stub WebApp in regular browsers — openLink is a no-op there.
  if (isMaxWebApp()) {
    const openLink = getWebApp()?.openLink
    if (openLink) {
      event.preventDefault()
      void openLink(url)
    }
  }
}

export function TransitHint({ leg, from, to }: TransitHintProps) {
  const isTaxi = leg.mode === 'taxi'
  const href = isTaxi
    ? yandexGoRouteUrl(from, to)
    : yandexMapsRouteUrl(from, to, leg.mode)
  const actionLabel = isTaxi ? 'Яндекс Go' : 'Карты'

  return (
    <div className={styles.hint}>
      <div className={styles.rail} aria-hidden>
        <span className={styles.line} />
        <span className={styles.mid}>
          {isTaxi ? <CarIcon /> : leg.mode === 'metro' ? <MetroIcon /> : <WalkIcon />}
        </span>
        <span className={styles.line} />
      </div>
      <div className={styles.copy}>
        <p className={styles.label}>{leg.label}</p>
        <a
          className={styles.action}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(event) => openExternal(event, href)}
        >
          {actionLabel}
          <ExternalIcon />
        </a>
      </div>
    </div>
  )
}

function ExternalIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M14 5h5v5M19 5l-9 9M10 5H5v14h14v-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
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

function MetroIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 17V9.5A5.5 5.5 0 0 1 12 4a5.5 5.5 0 0 1 8 5.5V17"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M7 17l2.5-8h5L17 17M6 17h3m6 0h3"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
