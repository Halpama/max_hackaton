import { useEffect, useState } from 'react'
import type { CityGuide } from '../model'
import { resolveCityImage } from '../lib/cityImage'
import { SoftImage } from './SoftImage'
import styles from './CityGuidePanel.module.css'

interface CityGuidePanelProps {
  city: string
  guide: CityGuide
}

/** Wikipedia descriptions often start with a capital; show as a soft subtitle. */
function softenSubtitle(text: string) {
  const value = text.trim()
  if (!value) return value
  return value.charAt(0).toLocaleLowerCase('ru-RU') + value.slice(1)
}

/** Drop SEO crumbs already baked into older route payloads. */
function isPracticalTip(item: string) {
  const text = item.trim()
  if (!text || text.length > 90) return false
  if (/[…]|\.\.\./.test(text)) return false
  if (/что посмотреть|гид по|сувенир|куда сходить|лучшие места/i.test(text)) {
    return false
  }
  return true
}

export function CityGuidePanel({ city, guide }: CityGuidePanelProps) {
  const [cover, setCover] = useState<string | null>(guide.imageUrl ?? null)
  const subtitle = guide.type.trim()
    ? softenSubtitle(guide.type)
    : null

  useEffect(() => {
    let cancelled = false
    if (guide.imageUrl) {
      setCover(guide.imageUrl)
      return
    }
    void resolveCityImage(city).then((url) => {
      if (!cancelled) setCover(url)
    })
    return () => {
      cancelled = true
    }
  }, [city, guide.imageUrl])

  // Skip lead if it only repeats the first sentence of «О городе».
  const lead = (() => {
    const summary = guide.summary.trim()
    if (!summary) return null
    const history = guide.history.trim()
    if (history && history.startsWith(summary.replace(/\.$/, ''))) return null
    if (subtitle && summary.toLocaleLowerCase('ru-RU').includes(subtitle.slice(0, 24))) {
      return null
    }
    return summary
  })()

  const tips = guide.highlights.filter(isPracticalTip)

  return (
    <section className={styles.wrap} aria-labelledby="trip-about-title">
      {cover ? (
        <div className={styles.cover}>
          <SoftImage src={cover} alt="" className={styles.coverImg} />
        </div>
      ) : null}

      <div className={styles.body}>
        <h2 id="trip-about-title" className={styles.title}>
          {city}
        </h2>
        {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}

        {lead ? <p className={styles.lead}>{lead}</p> : null}

        {guide.history ? (
          <div className={styles.block}>
            <h3 className={styles.label}>О городе</h3>
            <p className={styles.text}>{guide.history}</p>
          </div>
        ) : null}

        {tips.length > 0 ? (
          <div className={styles.block}>
            <h3 className={styles.label}>На заметку</h3>
            <ul className={styles.facts}>
              {tips.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className={styles.block}>
          <div className={styles.seasonHead}>
            <div>
              <h3 className={styles.label}>Сезон</h3>
              <p className={styles.seasonHint}>
                {guide.seasonalitySource === 'climate'
                  ? 'по климату за последние годы'
                  : 'оценка для прогулок'}
              </p>
            </div>
            <span className={styles.monthChip}>{guide.tripMonthLabel}</span>
          </div>
          <div
            className={styles.chart}
            role="img"
            aria-label={`Активность по месяцам. Поездка — ${guide.tripMonthLabel}`}
          >
            {guide.seasonality.map((item) => (
              <div
                key={item.month}
                className={item.isTripMonth ? styles.barActive : styles.bar}
                title={`${item.label}: ${item.level}`}
              >
                <span
                  className={styles.barFill}
                  style={{ height: `${item.score * 20}%` }}
                />
                <span className={styles.barLabel}>{item.label.slice(0, 3)}</span>
              </div>
            ))}
          </div>
        </div>

        {guide.sourceUrl && guide.sourceName ? (
          <p className={styles.source}>
            Источник:{' '}
            <a href={guide.sourceUrl} target="_blank" rel="noreferrer">
              {guide.sourceName}
            </a>
          </p>
        ) : null}
      </div>
    </section>
  )
}
