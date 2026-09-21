import type { DayPlan, DayWeather, WeatherIcon } from '../model'
import styles from './DayWeatherBadge.module.css'

/**
 * Compact weather strip for a day tab. Solid atmospheric washes only —
 * no particles or looping precip textures.
 */
export function DayWeatherBadge({ day }: { day: DayPlan }) {
  if (!day.weather) {
    return (
      <article className={styles.root} data-tone="muted">
        <div className={styles.body}>
          <span className={styles.glyph} aria-hidden>
            <CloudIcon />
          </span>
          <div className={styles.copy}>
            {day.dateLabel ? <span className={styles.date}>{day.dateLabel}</span> : null}
            <span className={styles.pending}>Прогноз появится ближе к дате</span>
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
        <span className={styles.glyph} aria-hidden>
          <WeatherGlyph icon={icon} />
        </span>
        <div className={styles.copy}>
          {day.dateLabel ? <span className={styles.date}>{day.dateLabel}</span> : null}
          <span className={styles.temps}>
            <span className={styles.tempHigh}>{formatTemp(tempHigh)}</span>
            <span className={styles.tempSep}>/</span>
            <span className={styles.tempLow}>{formatTemp(tempLow)}</span>
          </span>
          <span className={styles.summary}>{label}</span>
        </div>
        {rainy ? (
          <span className={styles.chip} title="Вероятность осадков">
            <DropIcon />
            {precipitationChance}%
          </span>
        ) : null}
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

function SunIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <circle cx="14" cy="14" r="5.5" fill="#FFCC33" />
      <g stroke="#FFB020" strokeWidth="2" strokeLinecap="round">
        <path d="M14 3.2v2.2M14 22.6v2.2M3.2 14h2.2M22.6 14h2.2M6.1 6.1l1.6 1.6M20.3 20.3l1.6 1.6M6.1 21.9l1.6-1.6M20.3 7.7l1.6-1.6" />
      </g>
    </svg>
  )
}

function CloudIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M8.2 19.8h12.4a4.4 4.4 0 0 0 .45-8.78A6.1 6.1 0 0 0 8 10.2a4.2 4.2 0 0 0 .2 9.6Z"
        fill="#EEF3F8"
        stroke="#C5D0DC"
        strokeWidth="1.2"
      />
      <path
        d="M10.4 17.2h9a3.1 3.1 0 0 0 .3-6.18A4.4 4.4 0 0 0 10.2 10a3 3 0 0 0 .2 7.2Z"
        fill="#FFFFFF"
        opacity="0.85"
      />
    </svg>
  )
}

function FogIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M5 11.2c2.2-1.4 4.6-.4 6.8.2 2.4.7 4.6 1.2 7-.2"
        stroke="#8FA3B8"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M4.5 15.4c2.6 1.2 5.2.2 7.6-.4 2.6-.6 5.2-.8 7.8.6"
        stroke="#A8B8C8"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M6 19.6c2.4-1 4.8-.2 7.1.3 2.5.6 5 .8 7.4-.3"
        stroke="#C0CCD8"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function RainIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M8 15.6h11.6a3.9 3.9 0 0 0 .4-7.78A5.4 5.4 0 0 0 7.8 6.6 3.7 3.7 0 0 0 8 15.6Z"
        fill="#E8EEF6"
      />
      <path d="M10.2 18.2 9 21.4" stroke="#7EB6FF" strokeWidth="2" strokeLinecap="round" />
      <path d="M14.2 17.8 13 21" stroke="#5B9CFF" strokeWidth="2" strokeLinecap="round" />
      <path d="M18.2 18.2 17 21.4" stroke="#7EB6FF" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function SleetIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M8 14.8h11.6a3.9 3.9 0 0 0 .4-7.78A5.4 5.4 0 0 0 7.8 5.8 3.7 3.7 0 0 0 8 14.8Z"
        fill="#E8EEF6"
      />
      <path d="M10.4 17.2 9.5 19.4" stroke="#7EB6FF" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M14.4 16.8 13.5 19" stroke="#7EB6FF" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="11.2" cy="22.2" r="1.3" fill="#D6E8FF" />
      <circle cx="16.4" cy="22.4" r="1.3" fill="#D6E8FF" />
    </svg>
  )
}

function SnowIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M14 5v18M7.6 8.8l12.8 10.4M20.4 8.8 7.6 19.2"
        stroke="#9ED0FF"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
      <path
        d="M10.4 6.8 14 5l3.6 1.8M10.4 21.2 14 23l3.6-1.8"
        stroke="#C7E4FF"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="14" cy="14" r="1.6" fill="#FFFFFF" />
    </svg>
  )
}

function StormIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M8 14.4h11.6a3.9 3.9 0 0 0 .4-7.78A5.4 5.4 0 0 0 7.8 5.4 3.7 3.7 0 0 0 8 14.4Z"
        fill="#D8DEE8"
      />
      <path
        d="m12.4 14.2 3.2-5.2h-2.2L15.8 15h-2.2l2 5.2-4.6-6h1.4Z"
        fill="#FFD166"
      />
    </svg>
  )
}

function DropIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 3c3.5 5 6 8.2 6 11a6 6 0 1 1-12 0c0-2.8 2.5-6 6-11Z"
        fill="currentColor"
      />
    </svg>
  )
}
