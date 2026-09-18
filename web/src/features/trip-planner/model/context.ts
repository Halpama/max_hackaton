import { createContext } from 'react'
import type { InterestId, Place, RoutePlan, TripDraft, TripPace, TripSummary } from './types'

export interface TripPlannerContextValue {
  draft: TripDraft
  route: RoutePlan
  trips: TripSummary[]
  favorites: Set<string>
  favoritePlaces: Place[]
  updateDraft: (patch: Partial<TripDraft>) => void
  toggleInterest: (id: InterestId) => void
  setPace: (pace: TripPace) => void
  setTravelers: (value: number) => void
  toggleFavorite: (placeId: string) => void
  isFavorite: (placeId: string) => boolean
  resetDraft: () => void
}

export const TripPlannerContext = createContext<TripPlannerContextValue | null>(null)
