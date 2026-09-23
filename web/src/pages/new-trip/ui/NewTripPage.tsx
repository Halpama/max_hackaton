import { useNavigate } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import { ROUTES } from "@/shared/config";
import {
    CityField,
    DateField,
    formatBudget,
    localDateIso,
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
} from "@/features/trip-planner";
import tripStyles from "@/features/trip-planner/ui/trip.module.css";

export function NewTripPage() {
    const navigate = useNavigate();
    const { draft, updateDraft, setAdults, setChildren } = useTripPlanner();

    const canContinue = draft.destination.trim().length > 0;
    const today = localDateIso();
    const startMin = today;
    const endMin = draft.startDate > today ? draft.startDate : today;

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
                hint={`Приезд — не раньше сегодня. Выезд по умолчанию через ${DEFAULT_TRIP_DURATION_DAYS} дня; короче минимальной длительности поставить нельзя.`}
            >
                <div className={tripStyles.datesStack}>
                    <div className={tripStyles.dateTimeRow}>
                        <DateField
                            label="Приезд"
                            value={draft.startDate}
                            min={startMin}
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
                            min={endMin}
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
                hint={`Сколько планируете потратить. 0 ₽ — только бесплатные места. До ${formatBudget(MAX_TRIP_BUDGET)} ₽.`}
            >
                <TextField
                    icon={<RubleIcon />}
                    inputMode="numeric"
                    value={formatBudget(draft.budget)}
                    onChange={(event) => {
                        const digits = event.target.value.replace(/\D/g, "");
                        updateDraft({ budget: digits ? Number(digits) : 0 });
                    }}
                />
            </Section>

            <Section
                label="Путешественники"
                hint="Укажите взрослых и детей. Всего может быть не больше 10 человек."
            >
                <div className={tripStyles.datesStack}>
                    <Stepper
                        icon={<PersonIcon />}
                        label="Взрослые"
                        value={draft.adults}
                        max={10 - draft.children}
                        onChange={setAdults}
                    />
                    <Stepper
                        icon={<PersonIcon />}
                        label="Дети"
                        value={draft.children}
                        min={0}
                        max={10 - draft.adults}
                        onChange={setChildren}
                    />
                </div>
            </Section>
        </Screen>
    );
}
