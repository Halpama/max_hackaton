import { useNavigate } from 'react-router-dom'
import { Button } from '@maxhub/max-ui'
import { ROUTES } from '@/shared/config'
import {
  DateField,
  formatBudget,
  formatTravelers,
  MAX_TRIP_BUDGET,
  PersonIcon,
  RubleIcon,
  Screen,
  SearchIcon,
  Section,
  Stepper,
  TextField,
  useTripPlanner,
} from '@/features/trip-planner'
import tripStyles from '@/features/trip-planner/ui/trip.module.css'

export function NewTripPage() {
  const navigate = useNavigate()
  const { draft, updateDraft, setTravelers } = useTripPlanner()

  return (
    <Screen
      footer={
        <Button stretched size="large" onClick={() => navigate(ROUTES.preferences)}>
          Далее
        </Button>
      }
    >
      <h1 className={tripStyles.title}>Новая поездка</h1>

      <Section
        label="Куда едем?"
        hint="Город или регион, куда хотите поехать."
      >
        <TextField
          icon={<SearchIcon />}
          value={draft.destination}
          onChange={(event) => updateDraft({ destination: event.target.value })}
          placeholder="Город или страна"
        />
      </Section>

      <Section
        label="Даты"
        hint="Выберите период поездки: день окончания не раньше дня начала."
      >
        <div className={tripStyles.grid2}>
          <DateField
            label="Начало"
            value={draft.startDate}
            max={draft.endDate}
            onChange={(startDate) => updateDraft({ startDate })}
          />
          <DateField
            label="Конец"
            value={draft.endDate}
            min={draft.startDate}
            onChange={(endDate) => updateDraft({ endDate })}
          />
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
