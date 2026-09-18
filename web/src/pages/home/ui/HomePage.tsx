import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Icon16SearchOutline } from '@maxhub/max-ui'
import { ROUTES } from '@/shared/config'
import {
  HomeTabs,
  Screen,
  StarIcon,
  useTripPlanner,
  type HomeTab,
  type Place,
  type TripSummary,
} from '@/features/trip-planner'
import tripStyles from '@/features/trip-planner/ui/trip.module.css'
import styles from '@/features/trip-planner/ui/home.module.css'

export function HomePage() {
  const navigate = useNavigate()
  const { trips, favoritePlaces } = useTripPlanner()
  const [tab, setTab] = useState<HomeTab>('trips')
  const [query, setQuery] = useState('')
  const [city, setCity] = useState('Все')

  const cities = useMemo(() => {
    const unique = [...new Set(favoritePlaces.map((place) => place.city))]
    return ['Все', ...unique]
  }, [favoritePlaces])

  const filteredFavorites = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return favoritePlaces.filter((place) => {
      const matchesCity = city === 'Все' || place.city === city
      const matchesQuery =
        !normalized ||
        place.title.toLowerCase().includes(normalized) ||
        place.category.toLowerCase().includes(normalized) ||
        place.city.toLowerCase().includes(normalized)
      return matchesCity && matchesQuery
    })
  }, [city, favoritePlaces, query])

  return (
    <Screen
      footer={
        tab === 'trips' ? (
          <Button stretched size="large" onClick={() => navigate(ROUTES.newTrip)}>
            Новая поездка
          </Button>
        ) : null
      }
    >
      <HomeTabs value={tab} onChange={setTab} />

      {tab === 'trips' ? (
        <TripsTab trips={trips} onOpenTrip={() => navigate(ROUTES.route)} />
      ) : (
        <FavoritesTab
          query={query}
          onQueryChange={setQuery}
          cities={cities}
          city={city}
          onCityChange={setCity}
          places={filteredFavorites}
          onOpenPlace={(placeId) => navigate(ROUTES.place(placeId))}
        />
      )}
    </Screen>
  )
}

function TripsTab({
  trips,
  onOpenTrip,
}: {
  trips: TripSummary[]
  onOpenTrip: (tripId: string) => void
}) {
  return (
    <div className={styles.stack}>
      <h1 className={tripStyles.title}>Мои поездки</h1>
      <div className={styles.list}>
        {trips.map((trip) => (
          <button
            key={trip.id}
            type="button"
            className={styles.card}
            onClick={() => onOpenTrip(trip.id)}
          >
            <div className={styles.copy}>
              <p className={styles.title}>{trip.city}</p>
              <p className={styles.subtitle}>
                {trip.dateLabel} · {trip.travelersLabel}
              </p>
            </div>
            <div className={styles.meta}>
              <span
                className={
                  trip.status === 'ready' ? styles.statusReady : styles.statusDraft
                }
              >
                {trip.status === 'ready' ? 'Готов' : 'Черновик'}
              </span>
              <p className={styles.budget}>{trip.budgetLabel}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function FavoritesTab({
  query,
  onQueryChange,
  cities,
  city,
  onCityChange,
  places,
  onOpenPlace,
}: {
  query: string
  onQueryChange: (value: string) => void
  cities: string[]
  city: string
  onCityChange: (value: string) => void
  places: Place[]
  onOpenPlace: (placeId: string) => void
}) {
  return (
    <div className={styles.stack}>
      <h1 className={tripStyles.title}>Избранное</h1>

      <Input
        mode="contrast"
        size="large"
        placeholder="Поиск по избранным"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        iconBefore={<Icon16SearchOutline />}
        withClearButton
      />

      <div className={styles.filters}>
        {cities.map((item) => (
          <button
            key={item}
            type="button"
            className={item === city ? styles.chipActive : styles.chip}
            onClick={() => onCityChange(item)}
          >
            {item}
          </button>
        ))}
      </div>

      {places.length === 0 ? (
        <p className={styles.empty}>Пока ничего не найдено</p>
      ) : (
        <div className={styles.list}>
          {places.map((place) => (
            <button
              key={place.id}
              type="button"
              className={styles.cardWide}
              onClick={() => onOpenPlace(place.id)}
            >
              <FavoriteThumb place={place} />
              <div className={styles.copy}>
                <p className={styles.title}>{place.title}</p>
                <p className={styles.subtitle}>
                  {place.city} · {shortCategory(place.category)}
                </p>
              </div>
              <span className={styles.rating}>
                <StarIcon />
                {place.rating}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function shortCategory(category: string) {
  const first = category.split(/[·,]/)[0]?.trim()
  return first && first.length <= 28 ? first : `${category.slice(0, 26)}…`
}

function FavoriteThumb({ place }: { place: Place }) {
  const [failed, setFailed] = useState(false)

  if (failed || !place.imageUrl) {
    return <div className={styles.thumbFallback} aria-hidden />
  }

  return (
    <img
      className={styles.thumb}
      src={place.imageUrl}
      alt=""
      onError={() => setFailed(true)}
    />
  )
}
