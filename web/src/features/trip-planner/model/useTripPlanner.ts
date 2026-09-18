import { useContext } from 'react'
import { TripPlannerContext } from './context'

export function useTripPlanner() {
  const ctx = useContext(TripPlannerContext)
  if (!ctx) {
    throw new Error('useTripPlanner must be used within TripPlannerProvider')
  }
  return ctx
}
