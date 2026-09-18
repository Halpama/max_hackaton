import { useMemo } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  FavoriteButton,
  MapIcon,
  PlaceDetails,
  Screen,
  SecondaryButton,
  useTripPlanner,
} from '@/features/trip-planner'
import tripStyles from '@/features/trip-planner/ui/trip.module.css'

export function LocationDetailPage() {
  const { placeId = '' } = useParams()
  const { route, isFavorite, toggleFavorite } = useTripPlanner()

  const place = useMemo(() => route.places[placeId], [placeId, route.places])

  if (!place) {
    return <Navigate to={ROUTES.route} replace />
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
                `https://yandex.ru/maps/?text=${encodeURIComponent(place.address)}`,
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
      <PlaceDetails place={place} />
    </Screen>
  )
}
