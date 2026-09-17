import type { ReactNode } from 'react'
import { MaxUI } from '@maxhub/max-ui'
import { MaxBridgeBootstrap } from './MaxBridgeBootstrap'

interface AppProvidersProps {
  children: ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <MaxUI>
      <MaxBridgeBootstrap>{children}</MaxBridgeBootstrap>
    </MaxUI>
  )
}
