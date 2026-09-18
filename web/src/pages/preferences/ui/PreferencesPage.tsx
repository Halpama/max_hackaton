import { useNavigate } from 'react-router-dom'
import { Button } from '@maxhub/max-ui'
import { ROUTES } from '@/shared/config'
import {
  InterestChips,
  OptionCard,
  PaceSegment,
  Screen,
  Section,
  useTripPlanner,
} from '@/features/trip-planner'

export function PreferencesPage() {
  const navigate = useNavigate()
  const { draft, toggleInterest, setPace, updateDraft } = useTripPlanner()

  return (
    <Screen
      footer={
        <Button stretched size="large" onClick={() => navigate(ROUTES.loading)}>
          Построить маршрут
        </Button>
      }
    >
      <Section label="Интересы">
        <InterestChips value={draft.interests} onToggle={toggleInterest} />
      </Section>

      <Section label="Темп поездки">
        <PaceSegment value={draft.pace} onChange={setPace} />
      </Section>

      <Section label="Дополнительно">
        <OptionCard
          title="Подобрать жилье"
          description="Рекомендации отелей от ИИ"
          checked={draft.findHousing}
          onChange={(checked) => updateDraft({ findHousing: checked })}
        />
      </Section>
    </Screen>
  )
}
