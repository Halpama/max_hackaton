import { useNavigate } from 'react-router-dom'
import { ROUTES } from '@/shared/config'
import {
  InterestChips,
  OptionCard,
  PaceSegment,
  PrimaryButton,
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
        <PrimaryButton onClick={() => navigate(ROUTES.loading)}>
          Построить маршрут
        </PrimaryButton>
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
