import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@maxhub/max-ui'
import { ROUTES, USE_MOCKS } from '@/shared/config'
import {
  InterestChips,
  PaceSegment,
  Screen,
  Section,
  useTripPlanner,
} from '@/features/trip-planner'
import { createTrip } from '@/features/trip-planner/api'

export function PreferencesPage() {
  const navigate = useNavigate()
  const { draft, toggleInterest, setPace } = useTripPlanner()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // The trip is created here rather than on the loading screen so a remount
  // (React StrictMode does this in dev) can never create a duplicate trip.
  const handleSubmit = async () => {
    if (submitting) return

    if (USE_MOCKS) {
      navigate(ROUTES.loading)
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const trip = await createTrip(draft)
      navigate(`${ROUTES.loading}?tripId=${trip.id}`)
    } catch {
      setError('Не удалось создать поездку. Попробуйте ещё раз.')
      setSubmitting(false)
    }
  }

  return (
    <Screen
      footer={
        <Button
          stretched
          size="large"
          disabled={submitting}
          onClick={() => void handleSubmit()}
        >
          {submitting ? 'Создаём поездку…' : 'Построить маршрут'}
        </Button>
      }
    >
      <Section
        label="Интересы"
        hint="Что вам ближе: музеи, еда, прогулки — отметьте всё, что важно."
      >
        <InterestChips value={draft.interests} onToggle={toggleInterest} />
      </Section>

      <Section
        label="Темп поездки"
        hint="Спокойный — меньше дел в день, активный — насыщенный график."
      >
        <PaceSegment value={draft.pace} onChange={setPace} />
      </Section>

      {error ? (
        <p style={{ color: '#ef4444', fontSize: 14, fontWeight: 600, margin: 0 }}>
          {error}
        </p>
      ) : null}
    </Screen>
  )
}
