import type { ReactNode } from 'react'
import styles from './RouteMainTabs.module.css'

export type RouteMainTab = 'route' | 'packing' | 'budget'

interface TabDef {
  id: RouteMainTab
  label: string
  icon: ReactNode
}

interface RouteMainTabsProps {
  value: RouteMainTab
  onChange: (value: RouteMainTab) => void
  tabs: TabDef[]
}

export function RouteMainTabs({ value, onChange, tabs }: RouteMainTabsProps) {
  return (
    <div className={styles.tabs} role="tablist" aria-label="Разделы поездки">
      {tabs.map((tab) => {
        const active = tab.id === value
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={active ? styles.tabActive : styles.tab}
            onClick={() => onChange(tab.id)}
          >
            <span className={styles.icon} aria-hidden>
              {tab.icon}
            </span>
            <span className={styles.label}>{tab.label}</span>
          </button>
        )
      })}
    </div>
  )
}
