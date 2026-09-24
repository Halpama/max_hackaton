import { useEffect } from 'react'
import { Outlet, useLocation, useMatches, useNavigationType, useResolvedPath } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import { useMaxBackButton } from '@/shared/hooks'
import { BottomNav, shouldShowBottomNav } from '@/features/trip-planner'
import { ToshaOnboarding } from '@/features/onboarding'
import styles from './AppShell.module.css'

export function AppShell() {
  const location = useLocation()
  const matches = useMatches()
  const navigationType = useNavigationType()
  const homePath = useResolvedPath(ROUTES.home)
  const deepest = matches[matches.length - 1]
  const isHome = deepest?.pathname === homePath.pathname
  const showNav = shouldShowBottomNav(location.pathname)

  useMaxBackButton(!isHome)

  // Opening a place from halfway down the itinerary used to land mid-page.
  // Going back is left alone so the browser can restore the previous offset.
  useEffect(() => {
    if (navigationType === 'POP') return
    window.scrollTo(0, 0)
  }, [location.pathname, location.search, navigationType])

  return (
    <div className={styles.page} data-has-nav={showNav ? 'true' : 'false'}>
      <div key={location.pathname} className={styles.content}>
        <Outlet />
      </div>
      {showNav ? <BottomNav /> : null}
      <ToshaOnboarding />
    </div>
  )
}
