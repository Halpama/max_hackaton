import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { TripPlannerContext } from './context'
import { DEFAULT_TRIP_DRAFT, MOCK_ROUTE, MOCK_TRIPS } from './mock'
import type { InterestId, TripDraft, TripPace } from './types'

const INITIAL_FAVORITES = new Set(['hermitage', 'kazanKremlin', 'olympicPark'])

export function TripPlannerProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<TripDraft>(DEFAULT_TRIP_DRAFT)
  const [favorites, setFavorites] = useState<Set<string>>(() => new Set(INITIAL_FAVORITES))

  const updateDraft = useCallback((patch: Partial<TripDraft>) => {
    setDraft((prev) => ({ ...prev, ...patch }))
  }, [])

  const toggleInterest = useCallback((id: InterestId) => {
    setDraft((prev) => {
      const exists = prev.interests.includes(id)
      return {
        ...prev,
        interests: exists
          ? prev.interests.filter((item) => item !== id)
          : [...prev.interests, id],
      }
    })
  }, [])

  const setPace = useCallback((pace: TripPace) => {
    setDraft((prev) => ({ ...prev, pace }))
  }, [])

  const setTravelers = useCallback((value: number) => {
    setDraft((prev) => ({
      ...prev,
      travelers: Math.min(10, Math.max(1, value)),
    }))
  }, [])

  const toggleFavorite = useCallback((placeId: string) => {
    setFavorites((prev) => {
      const next = new Set(prev)
      if (next.has(placeId)) {
        next.delete(placeId)
      } else {
        next.add(placeId)
      }
      return next
    })
  }, [])

  const isFavorite = useCallback(
    (placeId: string) => favorites.has(placeId),
    [favorites],
  )

  const resetDraft = useCallback(() => {
    setDraft(DEFAULT_TRIP_DRAFT)
  }, [])

  const favoritePlaces = useMemo(
    () =>
      [...favorites]
        .map((id) => MOCK_ROUTE.places[id])
        .filter((place): place is NonNullable<typeof place> => Boolean(place)),
    [favorites],
  )

  const value = useMemo(
    () => ({
      draft,
      route: MOCK_ROUTE,
      trips: MOCK_TRIPS,
      favorites,
      favoritePlaces,
      updateDraft,
      toggleInterest,
      setPace,
      setTravelers,
      toggleFavorite,
      isFavorite,
      resetDraft,
    }),
    [
      draft,
      favorites,
      favoritePlaces,
      updateDraft,
      toggleInterest,
      setPace,
      setTravelers,
      toggleFavorite,
      isFavorite,
      resetDraft,
    ],
  )

  return (
    <TripPlannerContext.Provider value={value}>
      {children}
    </TripPlannerContext.Provider>
  )
}
