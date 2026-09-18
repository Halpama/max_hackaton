import styles from './HomeTabs.module.css'

export type HomeTab = 'trips' | 'favorites'

interface HomeTabsProps {
  value: HomeTab
  onChange: (value: HomeTab) => void
}

export function HomeTabs({ value, onChange }: HomeTabsProps) {
  return (
    <div className={styles.tabs} role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={value === 'trips'}
        className={value === 'trips' ? styles.tabActive : styles.tab}
        onClick={() => onChange('trips')}
      >
        Поездки
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === 'favorites'}
        className={value === 'favorites' ? styles.tabActive : styles.tab}
        onClick={() => onChange('favorites')}
      >
        Избранное
      </button>
    </div>
  )
}
