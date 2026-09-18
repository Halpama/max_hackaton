import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  ActivityCard,
  CalendarIcon,
  DayTabs,
  PersonIcon,
  Screen,
  TransitHint,
  useTripPlanner,
} from '@/features/trip-planner'
import { DayRouteMap } from '@/features/trip-planner/ui/DayRouteMap'
import styles from '@/features/trip-planner/ui/screens.module.css'

export function ReadyRoutePage() {
  const navigate = useNavigate()
  const { route } = useTripPlanner()
  const [activeDayId, setActiveDayId] = useState(route.days[0]?.id ?? '')

  const day = useMemo(
    () => route.days.find((item) => item.id === activeDayId) ?? route.days[0],
    [activeDayId, route.days],
  )

  const dayPlaces = useMemo(
    () =>
      (day?.activities ?? [])
        .map((activity) => route.places[activity.placeId])
        .filter((place): place is NonNullable<typeof place> => Boolean(place)),
    [day, route.places],
  )

  return (
    <Screen flush>
      <div className={styles.summary}>
        <div className={styles.top}>
          <h1 className={styles.city}>{route.city}</h1>
          <BudgetBadge label={route.budgetLabel} />
        </div>
        <p className={styles.meta}>
          <span className={styles.metaItem}>
            <CalendarIcon />
            {route.dateLabel}
          </span>
          <span className={styles.metaDot} />
          <span className={styles.metaItem}>
            <PersonIcon />
            {route.travelersLabel}
          </span>
        </p>
      </div>

      <div className={styles.mapWrap}>
        <DayRouteMap
          places={dayPlaces}
          legModes={(day?.transits ?? []).map((leg) => leg?.mode)}
        />
      </div>

      <div style={{ paddingTop: 14, paddingBottom: 4 }}>
        <DayTabs
          days={route.days.map(({ id, label }) => ({ id, label }))}
          activeId={day?.id ?? ''}
          onChange={setActiveDayId}
        />
      </div>

      <div className={styles.list} key={day?.id ?? 'day'}>
        {day?.activities.map((activity, index) => {
          const fromPlace = route.places[activity.placeId]
          const toPlace = route.places[day.activities[index + 1]?.placeId]
          const transit = day.transits[index]

          return (
            <div
              key={activity.id}
              className={styles.listItem}
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <ActivityCard
                activity={activity}
                onClick={() => navigate(ROUTES.place(activity.placeId))}
              />
              {transit && fromPlace && toPlace ? (
                <TransitHint
                  leg={transit}
                  from={fromPlace.coordinates}
                  to={toPlace.coordinates}
                />
              ) : null}
            </div>
          )
        })}
      </div>
    </Screen>
  )
}

function BudgetBadge({ label }: { label: string }) {
  const match = label.match(/^(~)?\s*([\d\s]+)\s*(₽|руб\.?)?$/)
  const prefix = match?.[1] ?? '~'
  const value = (match?.[2] ?? label).trim()
  const currency = match?.[3] ?? '₽'

  return (
    <span className={styles.badge}>
      <span className={styles.badgePrefix}>{prefix}</span>
      <span className={styles.badgeValue}>{value}</span>
      <span className={styles.badgeCurrency}>{currency}</span>
    </span>
  )
}
