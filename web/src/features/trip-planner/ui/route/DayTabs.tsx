import styles from './DayTabs.module.css'

interface DayTabsProps {
  days: Array<{ id: string; label: string }>
  activeId: string
  onChange: (id: string) => void
}

export function DayTabs({ days, activeId, onChange }: DayTabsProps) {
  return (
    <div className={styles.tabs} role="tablist">
      {days.map((day) => (
        <button
          key={day.id}
          type="button"
          role="tab"
          aria-selected={day.id === activeId}
          className={day.id === activeId ? styles.tabActive : styles.tab}
          onClick={() => onChange(day.id)}
        >
          {day.label}
        </button>
      ))}
    </div>
  )
}
