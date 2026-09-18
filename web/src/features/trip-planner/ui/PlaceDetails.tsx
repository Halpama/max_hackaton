import { useState } from 'react'
import type { Place } from '../model'
import { FoodIcon, MuseumIcon, PinIcon, StarIcon, WalkIcon } from './icons'
import styles from './PlaceHero.module.css'

interface PlaceDetailsProps {
  place: Place
}

export function PlaceDetails({ place }: PlaceDetailsProps) {
  return (
    <>
      <PlaceHeroImage
        key={place.id}
        src={place.imageUrl}
        alt={place.title}
        categoryKind={place.categoryKind}
      />
      <div className={styles.content}>
        <div className={styles.head}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{place.title}</h1>
            <span className={styles.rating}>
              <StarIcon />
              {place.rating} · {place.reviewsLabel}
            </span>
          </div>
          <p className={styles.category}>
            <span className={styles.categoryIcon}>
              <CategoryIcon kind={place.categoryKind} />
            </span>
            {place.category}
          </p>
        </div>

        <div className={styles.info}>
          <InfoRow label="Время визита" value={place.timeRange} tone="primary" />
          <div className={styles.divider} />
          <InfoRow label="Продолжительность" value={place.durationLabel} />
          <div className={styles.divider} />
          <InfoRow label="Стоимость" value={place.priceLabel} tone="success" />
          <div className={styles.divider} />
          <InfoRow label="Адрес" value={place.address} tone="muted" />
        </div>

        <div className={styles.about}>
          <p className={styles.aboutLabel}>О месте</p>
          <p className={styles.aboutText}>{place.description}</p>
        </div>
      </div>
    </>
  )
}

function PlaceHeroImage({
  src,
  alt,
  categoryKind,
}: {
  src: string
  alt: string
  categoryKind: Place['categoryKind']
}) {
  const [failed, setFailed] = useState(false)

  if (failed || !src) {
    return (
      <div className={styles.heroFallback} role="img" aria-label={alt}>
        <div className={styles.heroFallbackGlow} aria-hidden />
        <div className={styles.heroFallbackIcon}>
          <CategoryIcon kind={categoryKind} />
        </div>
      </div>
    )
  }

  return (
    <img
      className={styles.hero}
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
    />
  )
}

function CategoryIcon({ kind }: { kind: Place['categoryKind'] }) {
  if (kind === 'museum') return <MuseumIcon />
  if (kind === 'food') return <FoodIcon />
  if (kind === 'walk') return <WalkIcon />
  return <PinIcon />
}

function InfoRow({
  label,
  value,
  tone = 'default',
}: {
  label: string
  value: string
  tone?: 'default' | 'primary' | 'success' | 'muted'
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
      <p className={styles.rowLabel}>{label}</p>
      <p className={valueClass}>{value}</p>
    </div>
  )
}
