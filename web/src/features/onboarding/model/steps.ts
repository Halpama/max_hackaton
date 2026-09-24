import type { TourId } from "../lib/storage";

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
    /** `data-tour` value(s) to spotlight; omit for a full-screen beat. */
    target?: string | string[];
    /** Prefer bubble above or below the hole when a target is set. */
    bubble?: "auto" | "above" | "below" | "center";
    cta?: string;
    /**
     * Path prefixes where this step is valid.
     * If set and the user is elsewhere, Tosha waits with a bridge message.
     */
    paths?: string[];
};

export const TOSHA_POSES: Record<ToshaPose, string> = {
    greetings: "/tosha/greetings.png",
    pointing: "/tosha/pointing.png",
    explaining: "/tosha/explaining.png",
    thinking: "/tosha/thinking.png",
    success: "/tosha/success.png",
};

export const HOME_TOUR_STEPS: OnboardingStep[] = [
    {
        id: "hello",
        pose: "greetings",
        title: "Привет! Я Тоша",
        text: "Проведу тебя по 2РИСТ за минуту — как в мини-игре. Можно пропустить в любой момент.",
        bubble: "center",
        cta: "Поехали!",
        paths: ["/"],
    },
    {
        id: "new-trip",
        pose: "pointing",
        title: "Собери маршрут",
        text: "Синяя кнопка «+» — старт новой поездки: город, даты, бюджет и интересы.",
        target: "nav-new",
        bubble: "above",
        cta: "Дальше",
        paths: ["/"],
    },
    {
        id: "trips",
        pose: "explaining",
        title: "Твои поездки здесь",
        text: "Готовые маршруты живут на главной. Открой карточку — внутри дни, карта, сборы и бюджет.",
        target: "home-trips",
        bubble: "below",
        cta: "Дальше",
        paths: ["/"],
    },
    {
        id: "help",
        pose: "thinking",
        title: "Подсказка всегда рядом",
        text: "Кнопка «i» — короткая памятка. А ещё отсюда можно снова позвать меня.",
        target: "home-help",
        bubble: "below",
        cta: "Дальше",
        paths: ["/"],
    },
    {
        id: "favorites",
        pose: "pointing",
        title: "Избранное",
        text: "Сердечко внизу — места, которые сохранил из маршрута. Удобно вернуться позже.",
        target: "nav-favorites",
        bubble: "above",
        cta: "Дальше",
        paths: ["/"],
    },
    {
        id: "done",
        pose: "success",
        title: "Готово — можно в путь!",
        text: "Жми «+», собери первую поездку — там я тоже подскажу по шагам.",
        bubble: "center",
        cta: "Начать",
        paths: ["/"],
    },
];

export const CREATE_TOUR_STEPS: OnboardingStep[] = [
    {
        id: "create-hello",
        pose: "greetings",
        title: "Собираем поездку",
        text: "Здесь задаёшь основу маршрута. Пройдёмся по полям — потом ИИ всё склеит по дням.",
        bubble: "center",
        cta: "Ок!",
        paths: ["/trips/new"],
    },
    {
        id: "create-city",
        pose: "pointing",
        title: "Куда едем?",
        text: "Выбери город из подсказок — так места и карта будут точнее.",
        target: "create-city",
        bubble: "below",
        cta: "Дальше",
        paths: ["/trips/new"],
    },
    {
        id: "create-dates",
        pose: "explaining",
        title: "Даты и время",
        text: "Приезд и выезд. От этого зависит, сколько дней появится в маршруте.",
        target: "create-dates",
        bubble: "below",
        cta: "Дальше",
        paths: ["/trips/new"],
    },
    {
        id: "create-budget",
        pose: "thinking",
        title: "Бюджет",
        text: "Сколько планируешь потратить. 0 ₽ — покажем в основном бесплатные места.",
        target: "create-budget",
        bubble: "below",
        cta: "Дальше",
        paths: ["/trips/new"],
    },
    {
        id: "create-party",
        pose: "pointing",
        title: "Кто едет",
        text: "Взрослые и дети — до 10 человек. Это влияет на цены и подсказки.",
        target: "create-party",
        bubble: "above",
        cta: "Дальше",
        paths: ["/trips/new"],
    },
    {
        id: "create-next",
        pose: "success",
        title: "Теперь заполни форму",
        text: "Город, даты, бюджет и состав — потом «Далее». На экране интересов я ещё раз коротко подскажу.",
        target: "create-next",
        bubble: "above",
        cta: "Понял",
        paths: ["/trips/new"],
    },
];

export const PREFS_TOUR_STEPS: OnboardingStep[] = [
    {
        id: "pref-bridge",
        pose: "explaining",
        title: "Интересы и темп",
        text: "Здесь настраиваем вкус поездки. Коротко по полям — и можно строить маршрут.",
        bubble: "center",
        cta: "Дальше",
        paths: ["/preferences"],
    },
    {
        id: "pref-interests",
        pose: "pointing",
        title: "Интересы",
        text: "Музеи, еда, прогулки — отмечай всё, что важно. Можно несколько.",
        target: "pref-interests",
        bubble: "below",
        cta: "Дальше",
        paths: ["/preferences"],
    },
    {
        id: "pref-pace",
        pose: "thinking",
        title: "Темп поездки",
        text: "Спокойный — меньше точек в день, активный — насыщенный график.",
        target: "pref-pace",
        bubble: "below",
        cta: "Дальше",
        paths: ["/preferences"],
    },
    {
        id: "pref-build",
        pose: "success",
        title: "Построить маршрут",
        text: "Большая кнопка внизу запускает ИИ. Можно подождать на экране загрузки.",
        target: "pref-build",
        bubble: "above",
        cta: "Готово",
        paths: ["/preferences"],
    },
];

export const ROUTE_TOUR_STEPS: OnboardingStep[] = [
    {
        id: "route-hello",
        pose: "success",
        title: "Маршрут готов!",
        text: "Я собрал дни, места и дороги. Коротко покажу, куда тыкать.",
        bubble: "center",
        cta: "Показать",
        paths: ["/route"],
    },
    {
        id: "route-header",
        pose: "explaining",
        title: "Город и меню",
        text: "Сверху — город и даты. Три точки — изменить параметры или удалить поездку.",
        target: "route-header",
        bubble: "below",
        cta: "Дальше",
        paths: ["/route"],
    },
    {
        id: "route-days",
        pose: "pointing",
        title: "Дни поездки",
        text: "«О поездке» — гид по городу. Дальше — дни: листай и смотри план.",
        target: "route-days",
        bubble: "below",
        cta: "Дальше",
        paths: ["/route"],
    },
    {
        id: "route-map",
        pose: "thinking",
        title: "Карта дня",
        text: "Точки на карте — места дня. Ниже — карточки с временем и дорогой между ними.",
        target: "route-map",
        bubble: "above",
        cta: "Дальше",
        paths: ["/route"],
    },
    {
        id: "route-nav",
        pose: "pointing",
        title: "Сборы и бюджет",
        text: "Внизу: «Сборы» — чеклист вещей, «Бюджет» — учёт трат. «Поездки» — назад к списку.",
        target: ["nav-packing", "nav-budget", "nav-trips"],
        bubble: "above",
        cta: "Дальше",
        paths: ["/route"],
    },
    {
        id: "route-done",
        pose: "greetings",
        title: "Приятной поездки!",
        text: "Открывай места, сохраняй в избранное и правь параметры, если планы изменились.",
        bubble: "center",
        cta: "Погнали",
        paths: ["/route"],
    },
];

export const TOUR_STEPS: Record<TourId, OnboardingStep[]> = {
    home: HOME_TOUR_STEPS,
    create: CREATE_TOUR_STEPS,
    prefs: PREFS_TOUR_STEPS,
    route: ROUTE_TOUR_STEPS,
};

/** @deprecated use HOME_TOUR_STEPS */
export const ONBOARDING_STEPS = HOME_TOUR_STEPS;

export function stepMatchesPath(step: OnboardingStep, pathname: string) {
    if (!step.paths || step.paths.length === 0) return true;
    return step.paths.some((path) => {
        if (path === "/") return pathname === "/" || pathname === "";
        return pathname === path || pathname.startsWith(`${path}/`);
    });
}

export function tourHomePath(tour: TourId): string {
    if (tour === "create") return "/trips/new";
    if (tour === "prefs") return "/preferences";
    if (tour === "route") return "/route";
    return "/";
}
