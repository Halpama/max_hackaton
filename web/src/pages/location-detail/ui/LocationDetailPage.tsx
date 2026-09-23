import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  FavoriteButton,
  LoadingView,
  MapIcon,
  PlaceDetails,
  Screen,
  SecondaryButton,
  StatusView,
  WarningIcon,
  useTripPlanner,
  type Place,
} from '@/features/trip-planner'
import { getPlace } from '@/features/trip-planner/api'
import {
  tripRoutePath,
  type PlaceNavState,
} from '@/features/trip-planner/ui/BottomNav'
import { yandexMapsPointUrl } from '@/shared/lib/yandex'
import tripStyles from '@/features/trip-planner/ui/trip.module.css'

function readNavState(state: unknown): PlaceNavState | null {
  if (!state || typeof state !== 'object') return null
  const navFrom = (state as PlaceNavState).navFrom
  if (navFrom !== 'trip' && navFrom !== 'favorites') return null
  return state as PlaceNavState
}

export function LocationDetailPage() {
  const { placeId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { isFavorite, toggleFavorite, findPlace, activeTripId } = useTripPlanner()

  const cached = findPlace(placeId)
  const [fetched, setFetched] = useState<Place | undefined>(undefined)
  const [failed, setFailed] = useState(false)
  const place = cached ?? (fetched?.id === placeId ? fetched : undefined)

  const navState = readNavState(location.state)
  const fromFavorites = navState?.navFrom === 'favorites'
  const backTarget = fromFavorites
    ? `${ROUTES.home}?tab=favorites`
    : tripRoutePath(navState?.tripId ?? activeTripId, navState?.dayId)

  // Deep links and reloads land here without the route in memory.
  useEffect(() => {
    if (cached) return

    let cancelled = false

    getPlace(placeId)
      .then((loaded) => {
        if (!cancelled) setFetched(loaded)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
    }
  }, [placeId, cached])

  if (!place) {
    return (
      <Screen>
        {failed ? (
          <StatusView
            tone="error"
            icon={<WarningIcon />}
            title="Место не найдено"
            text="Возможно, оно относится к удалённой поездке."
            actionLabel="Назад"
            onAction={() => navigate(backTarget, { replace: true })}
          />
        ) : (
          <LoadingView title="Загружаем место…" />
        )}
      </Screen>
    )
  }

  const favorite = isFavorite(place.id)

  return (
    <Screen
      flush
      footer={
        <div className={tripStyles.footerRow}>
          <SecondaryButton
            onClick={() => {
              window.open(
                yandexMapsPointUrl(place.coordinates),
                '_blank',
                'noopener,noreferrer',
              )
            }}
          >
            <MapIcon />
            На карте
          </SecondaryButton>
          <FavoriteButton active={favorite} onClick={() => toggleFavorite(place.id)} />
        </div>
      }
    >
      <PlaceDetails place={place} pricing={fromFavorites ? 'solo' : 'party'} />
    </Screen>
  )
}
