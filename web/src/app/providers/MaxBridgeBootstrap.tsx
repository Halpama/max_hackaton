import { useEffect, type ReactNode } from 'react'
import { notifyWebAppReady } from '@/shared/lib/max'

interface MaxBridgeBootstrapProps {
  children: ReactNode
}

/** Calls WebApp.ready() once on mount. */
export function MaxBridgeBootstrap({ children }: MaxBridgeBootstrapProps) {
  useEffect(() => {
    notifyWebAppReady()
  }, [])

  return children
}
