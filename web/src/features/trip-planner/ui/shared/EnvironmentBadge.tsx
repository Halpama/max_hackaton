import type { Place } from '../../model'
import styles from './EnvironmentBadge.module.css'

type KnownEnvironmentKind = Exclude<NonNullable<Place['environmentKind']>, 'unknown'>

const LABELS: Record<KnownEnvironmentKind, string> = {
  indoor: 'В помещении',
  outdoor: 'На улице',
  mixed: 'Смешанное',
}

export function EnvironmentBadge({ kind }: { kind?: Place['environmentKind'] }) {
  if (!kind || kind === 'unknown') return null

  return (
    <span className={styles.badge} data-kind={kind} title={LABELS[kind]}>
      <EnvironmentIcon kind={kind} />
      <span>{LABELS[kind]}</span>
    </span>
  )
}

function EnvironmentIcon({ kind }: { kind: KnownEnvironmentKind }) {
  if (kind === 'indoor') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
        <path d="M4.5 10.5 12 4l7.5 6.5M6.5 10v9.5h11V10" />
        <path d="M9 19.5v-5h6v5" />
      </svg>
    )
  }

  if (kind === 'outdoor') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="3.5" />
        <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path d="M4 18.5h16M5.5 18.5v-7h6v7M12.5 18.5v-7h6v7M4.5 11.5 12 5l7.5 6.5" />
    </svg>
  )
}