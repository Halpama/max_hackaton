import type { ReactNode } from 'react'
import { MaxUI } from '@maxhub/max-ui'
import { TripPlannerProvider } from '@/features/trip-planner'
import { MaxBridgeBootstrap } from './MaxBridgeBootstrap'

interface AppProvidersProps {
  children: ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <MaxUI colorScheme="light">
      <TripPlannerProvider>
        <MaxBridgeBootstrap>{children}</MaxBridgeBootstrap>
      </TripPlannerProvider>
    </MaxUI>
  )
}
