import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ROUTES, USE_MOCKS } from '@/shared/config'
import {
  LOADING_STEPS,
  LoadingOrb,
  ProgressSteps,
  Screen,
  StatusView,
  WarningIcon,
  useTripPlanner,
} from '@/features/trip-planner'
import { retryTrip, streamTrip } from '@/features/trip-planner/api'
import styles from '@/features/trip-planner/ui/shared/screens.module.css'

export function RouteLoadingPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { adoptRoute, refreshTrips } = useTripPlanner()

  const tripId = searchParams.get('tripId')
  const [activeIndex, setActiveIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (USE_MOCKS) {
      const timer = window.setTimeout(() => navigate(ROUTES.route, { replace: true }), 1200)
      return () => window.clearTimeout(timer)
    }

    if (!tripId) return

    const controller = new AbortController()
    let cancelled = false

    // Subscribing is idempotent: the backend replays the stages it already
    // published, so a remount picks up mid-generation without losing progress.
    const run = async () => {
      try {
        if (attempt > 0) await retryTrip(tripId)

        await streamTrip(
          tripId,
          {
            onStage: (event) => {
              if (cancelled) return
              // A finished stage moves the indicator onto the next one.
              setActiveIndex(event.status === 'done' ? event.index + 1 : event.index)
            },
            onDone: (route) => {
              if (cancelled) return
              adoptRoute(tripId, route)
              void refreshTrips()
              navigate(`${ROUTES.route}?tripId=${tripId}`, { replace: true })
            },
            onError: (message) => {
              if (!cancelled) setError(message)
            },
          },
          controller.signal,
        )
      } catch (cause) {
        if (cancelled) return
        setError(
          cause instanceof Error && cause.message.includes('VITE_API_BASE_URL')
            ? 'Бэкенд не настроен: задайте VITE_API_BASE_URL в web/.env'
            : 'Не удалось связаться с сервером',
        )
      }
    }

    void run()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [adoptRoute, navigate, refreshTrips, tripId, attempt])

  const handleRetry = useCallback(() => {
    if (!tripId) {
      navigate(ROUTES.newTrip)
      return
    }
    setError(null)
    setActiveIndex(0)
    setAttempt((prev) => prev + 1)
  }, [navigate, tripId])

  // Landing here without a trip id means the wizard was skipped or the link is stale.
  const message = !USE_MOCKS && !tripId ? 'Поездка не найдена. Начните заново.' : error

  if (message) {
    return (
      <Screen>
        <StatusView
          tone="error"
          icon={<WarningIcon />}
          title="Маршрут не собрался"
          text={message}
          actionLabel={tripId ? 'Попробовать снова' : 'Новая поездка'}
          onAction={handleRetry}
          secondaryActionLabel="На главную"
          onSecondaryAction={() => navigate(ROUTES.home, { replace: true })}
        />
      </Screen>
    )
  }

  const stepIndex = Math.min(activeIndex, LOADING_STEPS.length - 1)

  return (
    <Screen>
      <div className={styles.loadingCenter}>
        <LoadingOrb />
        <div className={styles.loadingCopy}>
          <h1 className={styles.loadingTitle}>ИИ составляет маршрут</h1>
          <p className={styles.loadingSub}>
            Анализируем предпочтения и собираем идеальный день
          </p>
        </div>
        <div className={styles.progressWrap}>
          <ProgressSteps steps={LOADING_STEPS} activeIndex={stepIndex} />
        </div>
      </div>
    </Screen>
  )
}
