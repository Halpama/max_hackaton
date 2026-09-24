import type { DayPlan, DayWeather, WeatherIcon } from '../../model'
import styles from './DayWeatherBadge.module.css'

/**
 * Compact weather strip for a day tab — quiet typography, no icon frame.
 */
export function DayWeatherBadge({ day }: { day: DayPlan }) {
  if (!day.weather) {
    return (
      <article className={styles.root} data-tone="muted">
        <div className={styles.body}>
          <span className={styles.icon} aria-hidden>
            <CloudIcon />
          </span>
          <div className={styles.copy}>
            {day.dateLabel ? (
              <span className={styles.date}>{day.dateLabel}</span>
            ) : null}
            <span className={styles.pending}>Прогноз ближе к дате</span>
          </div>
        </div>
      </article>
    )
  }

  const { label, icon, tempHigh, tempLow, precipitationChance } = day.weather
  const rainy = precipitationChance != null && precipitationChance >= 40

  return (
    <article className={styles.root} data-tone={icon}>
      <div className={styles.body}>
        <span className={styles.icon} aria-hidden>
          <WeatherGlyph icon={icon} />
        </span>
        <div className={styles.copy}>
          {day.dateLabel ? (
            <span className={styles.date}>{day.dateLabel}</span>
          ) : null}
          <div className={styles.tempsRow}>
            <span className={styles.temps}>
              <span className={styles.tempHigh}>{formatTemp(tempHigh)}</span>
              <span className={styles.tempSep}>/</span>
              <span className={styles.tempLow}>{formatTemp(tempLow)}</span>
            </span>
            {rainy ? (
              <span className={styles.precip} title="Вероятность осадков">
                {precipitationChance}%
              </span>
            ) : null}
          </div>
          <span className={styles.summary}>{label}</span>
        </div>
      </div>
    </article>
  )
}

function formatTemp(value: DayWeather['tempHigh']) {
  return `${value > 0 ? '+' : ''}${value}°`
}

function WeatherGlyph({ icon }: { icon: WeatherIcon }) {
  switch (icon) {
    case 'clear':
      return <SunIcon />
    case 'cloudy':
      return <CloudIcon />
    case 'fog':
      return <FogIcon />
    case 'rain':
      return <RainIcon />
    case 'sleet':
      return <SleetIcon />
    case 'snow':
      return <SnowIcon />
    case 'storm':
      return <StormIcon />
  }
}

/** Line icons, currentColor — sit flush without a tile behind them. */

function SunIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <circle cx="16" cy="16" r="5" stroke="currentColor" strokeWidth="1.6" />
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
        <path d="M16 5v2.2M16 24.8V27M5 16h2.2M24.8 16H27" />
        <path d="m8.2 8.2 1.5 1.5M22.3 22.3l1.5 1.5M8.2 23.8l1.5-1.5M22.3 9.7l1.5-1.5" />
      </g>
    </svg>
  )
}

function CloudIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <path
        d="M9.5 21.5h12.2a3.8 3.8 0 0 0 .35-7.58A5.4 5.4 0 0 0 11.2 12a3.6 3.6 0 0 0-1.7 9.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function FogIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
        <path d="M7 12.5h14" />
        <path d="M9 16.5h16" />
        <path d="M7 20.5h13" />
      </g>
    </svg>
  )
}

function RainIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <path
        d="M9.5 16.5h12.2a3.6 3.6 0 0 0 .3-7.16A5 5 0 0 0 11 8a3.4 3.4 0 0 0-1.5 8.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="m11.5 19.5-.8 2.4" />
        <path d="m16 19.2-.8 2.4" />
        <path d="m20.5 19.5-.8 2.4" />
      </g>
    </svg>
  )
}

function SleetIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <path
        d="M9.5 15.5h12.2a3.6 3.6 0 0 0 .3-7.16A5 5 0 0 0 11 7a3.4 3.4 0 0 0-1.5 8.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="m12 18.2-.6 1.8M17.5 18-.6 1.8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="13.2" cy="23.2" r="1.1" fill="currentColor" />
      <circle cx="18.8" cy="23.4" r="1.1" fill="currentColor" />
    </svg>
  )
}

function SnowIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M16 7v18" />
        <path d="m9.5 10.5 13 11" />
        <path d="m22.5 10.5-13 11" />
      </g>
      <circle cx="16" cy="16" r="1.4" fill="currentColor" />
    </svg>
  )
}

function StormIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
      <path
        d="M9.5 15h12.2a3.6 3.6 0 0 0 .3-7.16A5 5 0 0 0 11 6.5 3.4 3.4 0 0 0 9.5 15Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="m14.2 14.5 2.8-4.5h-1.9L17.5 16h-1.9l1.7 4.6-4-6.1h.9Z"
        fill="currentColor"
      />
    </svg>
  )
}
