import type { Place } from '../model'
import { FoodIcon, LandmarkIcon, MuseumIcon, WalkIcon } from './icons'
import styles from './CategoryBadge.module.css'

type CategoryKind = Place['categoryKind']

const KIND_CLASS: Record<CategoryKind, string> = {
  museum: styles.museum,
  food: styles.food,
  walk: styles.walk,
  location: styles.location,
}

function isSculptureLabel(category?: string) {
  const label = (category ?? '').toLowerCase()
  return (
    label.includes('скульптур') ||
    label.includes('памятник') ||
    label.includes('монумент') ||
    label.includes('бюст') ||
    label.includes('стату')
  )
}

/** Resolve display kind — older routes may tag sculptures as walk. */
function resolveKind(kind: CategoryKind, category?: string): CategoryKind {
  if (isSculptureLabel(category)) return 'location'
  return kind
}

export function CategoryBadge({
  kind,
  category,
  size = 'md',
}: {
  kind: CategoryKind
  /** Human label — used so statues never show footprints. */
  category?: string
  size?: 'sm' | 'md'
}) {
  const resolved = resolveKind(kind, category)
  return (
    <span
      className={`${styles.badge} ${KIND_CLASS[resolved]} ${size === 'sm' ? styles.sm : styles.md}`}
      aria-hidden
    >
      <CategoryGlyph kind={resolved} category={category} />
    </span>
  )
}

export function CategoryGlyph({
  kind,
  category,
}: {
  kind: CategoryKind
  category?: string
}) {
  const resolved = resolveKind(kind, category)
  if (resolved === 'museum') return <MuseumIcon />
  if (resolved === 'food') return <FoodIcon />
  if (resolved === 'walk') return <WalkIcon />
  return <LandmarkIcon />
}
