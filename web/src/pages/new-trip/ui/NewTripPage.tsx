import { useNavigate } from 'react-router-dom'
import { Button } from '@maxhub/max-ui'
import { ROUTES } from '@/shared/config'
import {
  CityField,
  DateField,
  formatBudget,
  formatTravelers,
  MAX_TRIP_BUDGET,
  PersonIcon,
  RubleIcon,
  Screen,
  Section,
  Stepper,
  TextField,
  TimeField,
  useTripPlanner,
  DEFAULT_TRIP_DURATION_DAYS,
} from '@/features/trip-planner'
import tripStyles from '@/features/trip-planner/ui/trip.module.css'

export function NewTripPage() {
  const navigate = useNavigate()
  const { draft, updateDraft, setTravelers } = useTripPlanner()

  const canContinue = draft.destination.trim().length > 0

  return (
    <Screen
      footer={
        <Button
          stretched
          size="large"
          disabled={!canContinue}
          onClick={() => navigate(ROUTES.preferences)}
        >
          Далее
        </Button>
      }
    >
      <h1 className={tripStyles.title}>Новая поездка</h1>

      <Section
        label="Куда едем?"
        hint="Выберите город из списка — так маршрут строится точнее."
      >
        <CityField
          value={draft.destination}
          onChange={(destination) => updateDraft({ destination })}
          placeholder="Начните вводить город"
        />
      </Section>

      <Section
        label="Даты"
        hint={`Приезд — любой. Выезд по умолчанию через ${DEFAULT_TRIP_DURATION_DAYS} дня; короче минимальной длительности поставить нельзя.`}
      >
        <div className={tripStyles.datesStack}>
          <div className={tripStyles.dateTimeRow}>
            <DateField
              label="Приезд"
              value={draft.startDate}
              onChange={(startDate) => updateDraft({ startDate })}
            />
            <TimeField
              label="Время"
              value={draft.startTime}
              onChange={(startTime) => updateDraft({ startTime })}
            />
          </div>
          <div className={tripStyles.dateTimeRow}>
            <DateField
              label="Выезд"
              value={draft.endDate}
              onChange={(endDate) => updateDraft({ endDate })}
            />
            <TimeField
              label="Время"
              value={draft.endTime}
              onChange={(endTime) => updateDraft({ endTime })}
            />
          </div>
        </div>
      </Section>

      <Section
        label="Бюджет"
        hint={`Сколько планируете потратить на всю поездку. До ${formatBudget(MAX_TRIP_BUDGET)} ₽.`}
      >
        <TextField
          icon={<RubleIcon />}
          inputMode="numeric"
          value={formatBudget(draft.budget)}
          onChange={(event) => {
            const digits = event.target.value.replace(/\D/g, '')
            updateDraft({ budget: digits ? Number(digits) : 0 })
          }}
        />
      </Section>

      <Section
        label="Путешественники"
        hint="Сколько человек едет вместе."
      >
        <Stepper
          icon={<PersonIcon />}
          label={formatTravelers(draft.travelers)}
          value={draft.travelers}
          onChange={setTravelers}
        />
      </Section>
    </Screen>
  )
}
