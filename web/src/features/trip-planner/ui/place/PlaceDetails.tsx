import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { Place } from '../../model'
import { formatPlaceTitle } from '../../lib/format'
import { parseOpeningHours } from '../../lib/openingHours'
import { CategoryBadge } from '../shared/CategoryBadge'
import { EnvironmentBadge } from '../shared/EnvironmentBadge'
import { ChevronDownIcon, StarIcon } from '../shared/icons-sprite'
import { SoftImage } from '../shared/SoftImage'
import styles from './PlaceHero.module.css'

interface PlaceDetailsProps {
  place: Place
  /** Favourites have no trip party — show a per-person figure. */
  pricing?: 'party' | 'solo'
}

function formatMoneyRub(value: number): string {
  return `${Math.round(value).toLocaleString('ru-RU').replace(/\u00a0/g, ' ')} ₽`
}

/** Stored place payloads keep the trip party total; favourites should not. */
function withSoloPricing(place: Place): Place {
  if (place.priceValue == null || place.priceValue <= 0) return place

  const partyMatch = /на (\d+) чел/.exec(place.priceLabel)
  const party = partyMatch ? Number(partyMatch[1]) : 1
  if (!Number.isFinite(party) || party <= 1) {
    if (/за 1 чел/.test(place.priceLabel)) return place
    const approx = place.priceLabel.trimStart().startsWith('~')
    return {
      ...place,
      priceLabel: `${approx ? '~' : ''}${formatMoneyRub(place.priceValue)} · за 1 чел`,
    }
  }

  const unit = Math.max(50, Math.round(place.priceValue / party / 50) * 50)
  const approx = place.priceLabel.trimStart().startsWith('~')
  return {
    ...place,
    priceValue: unit,
    priceLabel: `${approx ? '~' : ''}${formatMoneyRub(unit)} · за 1 чел`,
  }
}

export function PlaceDetails({ place, pricing = 'party' }: PlaceDetailsProps) {
  const display = pricing === 'solo' ? withSoloPricing(place) : place
  const estimatedPrice = display.priceEstimated !== false && display.priceValue != null
  const title = formatPlaceTitle(display.title)
  const [hasHero, setHasHero] = useState(Boolean(display.imageUrl))

  useEffect(() => {
    setHasHero(Boolean(display.imageUrl))
  }, [display.id, display.imageUrl])

  return (
    <>
      {hasHero && display.imageUrl ? (
        <PlaceHeroImage
          key={display.id}
          src={display.imageUrl}
          alt={title}
          onGone={() => setHasHero(false)}
        />
      ) : null}
      <div className={hasHero ? styles.content : styles.contentNoHero}>
        <div className={styles.head}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{title}</h1>
            <span
              className={styles.rating}
              title={
                display.ratingSource === 'catalog'
                  ? 'Оценка по популярности места в каталоге'
                  : 'Приблизительная оценка: у источника нет отзывов'
              }
            >
              <StarIcon />
              {display.rating.toFixed(1)}
              {display.ratingSource === 'estimate' ? '*' : ''}
            </span>
          </div>
          <p className={styles.category}>
            <CategoryBadge kind={display.categoryKind} category={display.category} size="sm" />
            {display.category}
            {display.ratingSource === 'catalog' ? ` · ${display.reviewsLabel}` : ''}
            <EnvironmentBadge kind={display.environmentKind} />
          </p>
        </div>

        <div className={styles.info}>
          <InfoRow label="Время визита" value={display.timeRange} tone="primary" />
          <div className={styles.divider} />
          <InfoRow label="Продолжительность" value={display.durationLabel} />
          <div className={styles.divider} />
          <InfoRow
            label="Стоимость"
            value={display.priceLabel}
            tone="success"
            note={
              estimatedPrice
                ? 'Приблизительная оценка — уточняйте реальную цену'
                : undefined
            }
          />
          <div className={styles.divider} />
          <InfoRow label="Адрес" value={display.address} tone="muted" />
        </div>

        {display.openingHours ? <OpeningHoursBlock raw={display.openingHours} /> : null}

        <ExpandableAbout key={display.id} text={display.description} />

        {display.sourceUrl && display.sourceName ? (
          <a
            className={styles.source}
            href={display.sourceUrl}
            target="_blank"
            rel="noopener"
          >
            Источник: {display.sourceName}
          </a>
        ) : null}
      </div>
    </>
  )
}

function OpeningHoursBlock({ raw }: { raw: string }) {
  const rows = useMemo(() => parseOpeningHours(raw), [raw])

  return (
    <div className={styles.hours}>
      <p className={styles.hoursLabel}>Часы работы</p>
      <div className={styles.hoursCard}>
        {rows.map((row, index) => (
          <div key={`${row.days}-${row.hours}-${index}`} className={styles.hoursRow}>
            {row.days ? <span className={styles.hoursDays}>{row.days}</span> : null}
            <span className={styles.hoursTime}>{row.hours}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Long descriptions are clamped with a fade, so the page stays scannable. */
function ExpandableAbout({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const [clampable, setClampable] = useState(false)
  const textRef = useRef<HTMLParagraphElement>(null)

  // Whether the copy overflows depends on the rendered width, so it can only be
  // measured after layout.
  useLayoutEffect(() => {
    const node = textRef.current
    if (!node) return
    setClampable(node.scrollHeight - node.clientHeight > 4)
  }, [text])

  return (
    <div className={styles.about}>
      <p className={styles.aboutLabel}>О месте</p>
      <div className={styles.aboutBody}>
        <p
          ref={textRef}
          className={expanded ? styles.aboutText : styles.aboutTextClamped}
        >
          {text}
        </p>
        {clampable && !expanded ? <span className={styles.aboutFade} aria-hidden /> : null}
      </div>
      {clampable ? (
        <button
          type="button"
          className={styles.aboutToggle}
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          {expanded ? 'Свернуть' : 'Читать полностью'}
          <span className={expanded ? styles.aboutChevronUp : styles.aboutChevron}>
            <ChevronDownIcon />
          </span>
        </button>
      ) : null}
    </div>
  )
}

function PlaceHeroImage({
  src,
  alt,
  onGone,
}: {
  src: string
  alt: string
  onGone: () => void
}) {
  if (!src) return null

  return (
    <SoftImage
      className={styles.hero}
      skeletonClassName={styles.heroSkeleton}
      src={src}
      alt={alt}
      loading="eager"
      onError={onGone}
    />
  )
}

function InfoRow({
  label,
  value,
  tone = 'default',
  note,
}: {
  label: string
  value: string
  tone?: 'default' | 'primary' | 'success' | 'muted'
  note?: string
}) {
  const valueClass =
    tone === 'primary'
      ? styles.rowValuePrimary
      : tone === 'success'
        ? styles.rowValueSuccess
        : tone === 'muted'
          ? styles.rowValueMuted
          : styles.rowValue

  return (
    <div className={styles.row}>
      <div className={styles.rowMain}>
        <p className={styles.rowLabel}>{label}</p>
        <p className={styles.rowValueWrap}>
          <span className={valueClass}>{value}</span>
        </p>
      </div>
      {note ? <p className={styles.rowNote}>{note}</p> : null}
    </div>
  )
}
