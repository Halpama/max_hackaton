import { Outlet, useLocation, useMatches, useResolvedPath } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import { useMaxBackButton } from '@/shared/hooks'
import styles from './AppShell.module.css'

export function AppShell() {
  const location = useLocation()
  const matches = useMatches()
  const homePath = useResolvedPath(ROUTES.home)
  const deepest = matches[matches.length - 1]
  const isHome = deepest?.pathname === homePath.pathname

  useMaxBackButton(!isHome)

  return (
    <div key={location.pathname} className={styles.page}>
      <Outlet />
    </div>
  )
}
