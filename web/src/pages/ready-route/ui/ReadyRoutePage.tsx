import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  ActivityCard,
  CalendarIcon,
  CompassIcon,
  DayTabs,
  LoadingView,
  PersonIcon,
  Screen,
  StatusView,
  TransitHint,
  WarningIcon,
  useTripPlanner,
} from '@/features/trip-planner'
import { DayRouteMap } from '@/features/trip-planner/ui/DayRouteMap'
import { DayWeatherBadge } from '@/features/trip-planner/ui/DayWeatherBadge'
import { parseTripTab, placeNavState } from '@/features/trip-planner/ui/BottomNav'
import { PackingPanel } from '@/features/trip-planner/ui/PackingPanel'
import { BudgetPanel } from '@/features/trip-planner/ui/BudgetPanel'
import {
  formatMoney,
  useTripLocalState,
} from '@/features/trip-planner/model/useTripLocalState'
import styles from '@/features/trip-planner/ui/screens.module.css'

export function ReadyRoutePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { route, routeState, routeError, activeTripId, openTrip, draft } = useTripPlanner()

  const requestedTripId = searchParams.get('tripId')
  const mainTab = parseTripTab(searchParams.get('tab'))
  const [activeDayId, setActiveDayId] = useState('')

  // A link or reload can point at a different trip than the one in memory.
  useEffect(() => {
    if (requestedTripId && requestedTripId !== activeTripId) {
      void openTrip(requestedTripId)
    }
  }, [requestedTripId, activeTripId, openTrip])

  const day = useMemo(() => {
    if (!route) return undefined
    return route.days.find((item) => item.id === activeDayId) ?? route.days[0]
  }, [activeDayId, route])

  const dayPlaces = useMemo(() => {
    if (!route || !day) return []
    return day.activities
      .map((activity) => route.places[activity.placeId])
      .filter((place): place is NonNullable<typeof place> => Boolean(place))
  }, [day, route])

  const tripId = activeTripId ?? ''
  const plannedBudget = draft.budget > 0 ? draft.budget : 45_000

  const {
    packing,
    updatePacking,
    ledger,
    addLedgerEntry,
    removeLedgerEntry,
    remaining,
    spent,
    toppedUp,
    createId,
    todayIso,
  } = useTripLocalState(tripId, plannedBudget)

  if (!route) {
    if (routeState === 'loading' || routeState === 'idle') {
      return (
        <Screen>
          <LoadingView title="Загружаем маршрут…" />
        </Screen>
      )
    }

    return (
      <Screen>
        <StatusView
          tone="error"
          icon={<WarningIcon />}
          title="Маршрут недоступен"
          text={routeError ?? 'Создайте новую поездку, чтобы увидеть маршрут.'}
          actionLabel="Новая поездка"
          onAction={() => navigate(ROUTES.newTrip)}
        />
      </Screen>
    )
  }

  return (
    <Screen flush>
      <div className={styles.summary}>
        <div className={styles.top}>
          <h1 className={styles.city}>{route.city}</h1>
          <RemainingBadge remaining={remaining} />
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

      {mainTab === 'route' ? (
        <div key="route" className={styles.panel}>
          {day && day.activities.length > 0 ? (
            <>
              <div className={`${styles.mapWrap} ${styles.mapReveal}`}>
                <DayRouteMap
                  places={dayPlaces}
                  legModes={(day.transits ?? []).map((leg) => leg?.mode)}
                />
              </div>

              <div className={styles.dayControls}>
                <DayTabs
                  days={route.days.map(({ id, label }) => ({ id, label }))}
                  activeId={day.id}
                  onChange={setActiveDayId}
                />
                <DayWeatherBadge key={day.id} day={day} />
              </div>

              <div className={styles.list} key={day.id}>
                {day.activities.map((activity, index) => {
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
                        categoryKind={fromPlace?.categoryKind}
                        category={fromPlace?.category}
                        onClick={() =>
                          navigate(ROUTES.place(activity.placeId), {
                            state: placeNavState('trip'),
                          })
                        }
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
            </>
          ) : (
            <StatusView
              icon={<CompassIcon />}
              title="В этом дне пока пусто"
              text="Попробуйте создать поездку заново с другими интересами."
              actionLabel="Новая поездка"
              onAction={() => navigate(ROUTES.newTrip)}
            />
          )}
        </div>
      ) : null}

      {mainTab === 'packing' ? (
        <div key="packing" className={styles.panel}>
          <PackingPanel blocks={packing} onChange={updatePacking} createId={createId} />
        </div>
      ) : null}

      {mainTab === 'budget' ? (
        <div key="budget" className={styles.panel}>
          <BudgetPanel
            plannedBudget={plannedBudget}
            remaining={remaining}
            spent={spent}
            toppedUp={toppedUp}
            ledger={ledger}
            todayIso={todayIso}
            onAdd={addLedgerEntry}
            onRemove={removeLedgerEntry}
          />
        </div>
      ) : null}
    </Screen>
  )
}

function RemainingBadge({ remaining }: { remaining: number }) {
  const overspent = remaining < 0

  return (
    <span className={overspent ? styles.badgeWarn : styles.badge} title="Остаток бюджета">
      <span className={styles.badgeStack}>
        <span className={styles.badgePrefix}>{overspent ? 'Перерасход' : 'Осталось'}</span>
        <span className={styles.badgeAmount}>
          <span className={styles.badgeValue}>{formatMoney(Math.abs(remaining))}</span>
          <span className={styles.badgeCurrency}>₽</span>
        </span>
      </span>
    </span>
  )
}
