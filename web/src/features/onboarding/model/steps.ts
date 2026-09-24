export type ToshaPose =
    | "greetings"
    | "pointing"
    | "explaining"
    | "thinking"
    | "success";

export type OnboardingStep = {
    id: string;
    pose: ToshaPose;
    title: string;
    text: string;
    /** `data-tour` value to spotlight; omit for a full-screen beat. */
    target?: string;
    /** Prefer bubble above or below the hole when a target is set. */
    bubble?: "auto" | "above" | "below" | "center";
    cta?: string;
};

export const TOSHA_POSES: Record<ToshaPose, string> = {
    greetings: "/tosha/greetings.png",
    pointing: "/tosha/pointing.png",
    explaining: "/tosha/explaining.png",
    thinking: "/tosha/thinking.png",
    success: "/tosha/success.png",
};

export const ONBOARDING_STEPS: OnboardingStep[] = [
    {
        id: "hello",
        pose: "greetings",
        title: "Привет! Я Тоша",
        text: "Проведу тебя по 2РИСТ за минуту — как в мини-игре. Можно пропустить в любой момент.",
        bubble: "center",
        cta: "Поехали!",
    },
    {
        id: "new-trip",
        pose: "pointing",
        title: "Собери маршрут",
        text: "Синяя кнопка «+» — старт новой поездки: город, даты, бюджет и интересы.",
        target: "nav-new",
        bubble: "above",
        cta: "Дальше",
    },
    {
        id: "trips",
        pose: "explaining",
        title: "Твои поездки здесь",
        text: "Готовые маршруты живут на главной. Открой карточку — внутри дни, карта, сборы и бюджет.",
        target: "home-trips",
        bubble: "below",
        cta: "Дальше",
    },
    {
        id: "help",
        pose: "thinking",
        title: "Подсказка всегда рядом",
        text: "Кнопка «i» — короткая памятка. А ещё отсюда можно снова позвать меня.",
        target: "home-help",
        bubble: "below",
        cta: "Дальше",
    },
    {
        id: "favorites",
        pose: "pointing",
        title: "Избранное",
        text: "Сердечко внизу — места, которые сохранил из маршрута. Удобно вернуться позже.",
        target: "nav-favorites",
        bubble: "above",
        cta: "Дальше",
    },
    {
        id: "done",
        pose: "success",
        title: "Готово — можно в путь!",
        text: "Жми «+», собери первую поездку, а я буду рядом в маршрутах и подсказках.",
        bubble: "center",
        cta: "Начать",
    },
];
