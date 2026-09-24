import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import { ROUTES } from "@/shared/config";
import {
    CityField,
    DateField,
    formatBudget,
    InterestChips,
    localDateIso,
    MAX_TRIP_BUDGET,
    PaceSegment,
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
import { getTripEditDraft, updateTrip } from "@/features/trip-planner/api";
import tripStyles from "@/features/trip-planner/ui/shared/trip.module.css";

export function NewTripPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const editingTripId = searchParams.get("tripId");
    const isEditing = Boolean(editingTripId);
    const {
        draft,
        updateDraft,
        replaceDraft,
        setAdults,
        setChildren,
        toggleInterest,
        setPace,
    } = useTripPlanner();
    const [loadingEdit, setLoadingEdit] = useState(isEditing);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!editingTripId) {
            setLoadingEdit(false);
            return;
        }
        let cancelled = false;
        setLoadingEdit(true);
        void getTripEditDraft(editingTripId)
            .then((parameters) => {
                if (cancelled) return;
                // Destination stays server-owned and is not editable here.
                replaceDraft({
                    destination: "",
                    ...parameters,
                });
                setLoadingEdit(false);
            })
            .catch(() => {
                if (!cancelled) setLoadingEdit(false);
            });
        return () => {
            cancelled = true;
        };
    }, [editingTripId, replaceDraft]);

    const canContinue = isEditing
        ? !loadingEdit && !submitting
        : draft.destination.trim().length > 0 && !submitting;
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
                    onClick={() => {
                        if (!editingTripId) {
                            navigate(ROUTES.preferences);
                            return;
                        }
                        setSubmitting(true);
                        void updateTrip(editingTripId, {
                            startDate: draft.startDate,
                            startTime: draft.startTime,
                            endDate: draft.endDate,
                            endTime: draft.endTime,
                            budget: draft.budget,
                            adults: draft.adults,
                            children: draft.children,
                            interests: draft.interests,
                            pace: draft.pace,
                            findHousing: draft.findHousing,
                        })
                            .then(() =>
                                navigate(
                                    `${ROUTES.loading}?tripId=${editingTripId}`,
                                ),
                            )
                            .catch(() => setSubmitting(false));
                    }}
                >
                    {isEditing
                        ? submitting
                            ? "Сохраняем…"
                            : "Перестроить маршрут"
                        : "Далее"}
                </Button>
            }
        >
            <h1 className={tripStyles.title}>
                {isEditing ? "Изменить параметры" : "Новая поездка"}
            </h1>

            {!isEditing ? (
                <Section
                    label="Куда едем?"
                    hint="Выберите город из списка — так маршрут строится точнее."
                >
                    <CityField
                        value={draft.destination}
                        onChange={(destination) =>
                            updateDraft({ destination })
                        }
                        placeholder="Начните вводить город"
                    />
                </Section>
            ) : null}

            <Section
                label="Даты"
                hint={
                    isEditing
                        ? "Город остаётся прежним — меняются даты, бюджет, состав, интересы и темп."
                        : `Приезд — не раньше текущей даты. Выезд по умолчанию через ${DEFAULT_TRIP_DURATION_DAYS} дня.`
                }
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

            {isEditing ? (
                <>
                    <Section
                        label="Интересы"
                        hint="Что вам ближе: музеи, еда, прогулки — отметьте всё, что важно."
                    >
                        <InterestChips
                            value={draft.interests}
                            onToggle={toggleInterest}
                        />
                    </Section>

                    <Section
                        label="Темп поездки"
                        hint="Спокойный — меньше дел в день, активный — насыщенный график."
                    >
                        <PaceSegment value={draft.pace} onChange={setPace} />
                    </Section>
                </>
            ) : null}
        </Screen>
    );
}
