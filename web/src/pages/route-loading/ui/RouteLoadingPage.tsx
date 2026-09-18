import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  LOADING_STEPS,
  LoadingOrb,
  ProgressSteps,
  Screen,
} from '@/features/trip-planner'
import styles from '@/features/trip-planner/ui/screens.module.css'

export function RouteLoadingPage() {
  const navigate = useNavigate()
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (activeIndex >= LOADING_STEPS.length) {
      const timer = window.setTimeout(() => navigate(ROUTES.route, { replace: true }), 450)
      return () => window.clearTimeout(timer)
    }

    const timer = window.setTimeout(() => {
      setActiveIndex((prev) => prev + 1)
    }, 780)

    return () => window.clearTimeout(timer)
  }, [activeIndex, navigate])

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
