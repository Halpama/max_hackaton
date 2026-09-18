import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  ActivityCard,
  BagIcon,
  CalendarIcon,
  DayTabs,
  MapIcon,
  PersonIcon,
  RubleIcon,
  Screen,
  TransitHint,
  useTripPlanner,
} from '@/features/trip-planner'
import { DayRouteMap } from '@/features/trip-planner/ui/DayRouteMap'
import { RouteMainTabs, type RouteMainTab } from '@/features/trip-planner/ui/RouteMainTabs'
import { PackingPanel } from '@/features/trip-planner/ui/PackingPanel'
import { BudgetPanel } from '@/features/trip-planner/ui/BudgetPanel'
import {
  formatMoney,
  useTripLocalState,
} from '@/features/trip-planner/model/useTripLocalState'
import styles from '@/features/trip-planner/ui/screens.module.css'

export function ReadyRoutePage() {
  const navigate = useNavigate()
  const { route, draft } = useTripPlanner()
  const [mainTab, setMainTab] = useState<RouteMainTab>('route')
  const [activeDayId, setActiveDayId] = useState(route.days[0]?.id ?? '')

  const tripId = useMemo(
    () => `${route.city}-${route.dateLabel}`.toLowerCase().replace(/\s+/g, '-'),
    [route.city, route.dateLabel],
  )
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

      <div className={styles.mainTabs}>
        <RouteMainTabs
          value={mainTab}
          onChange={setMainTab}
          tabs={[
            { id: 'route', label: 'Маршрут', icon: <MapIcon /> },
            { id: 'packing', label: 'Сборы', icon: <BagIcon /> },
            { id: 'budget', label: 'Бюджет', icon: <RubleIcon /> },
          ]}
        />
      </div>

      {mainTab === 'route' ? (
        <>
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
        </>
      ) : null}

      {mainTab === 'packing' ? (
        <PackingPanel blocks={packing} onChange={updatePacking} createId={createId} />
      ) : null}

      {mainTab === 'budget' ? (
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
