import { Outlet, useMatches, useResolvedPath } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import { useMaxBackButton } from '@/shared/hooks'

export function AppShell() {
  const matches = useMatches()
  const homePath = useResolvedPath(ROUTES.home)
  const deepest = matches[matches.length - 1]
  const isHome = deepest?.pathname === homePath.pathname

  useMaxBackButton(!isHome)

  return <Outlet />
}
