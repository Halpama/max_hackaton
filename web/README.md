# 2РИСТ — WebApp (MAX)

Мини-приложение Trip Planner для мессенджера MAX: создание поездки, live-генерация маршрута по SSE, карта дня, гид по городу, packing и бюджет.

## Стек

- React 19 + TypeScript + Vite
- React Router
- `@maxhub/max-ui` + MAX WebApp bridge
- MapLibre (тайлы Yandex или OSM)
- Oxlint / Vitest

## Быстрый старт

```bash
cd web
cp .env.example .env   # если есть
npm install
npm run dev
```

Сборка: `npm run build`  
Тесты: `npm test`  
Линт: `npm run lint`

Локально API обычно на `VITE_API_BASE_URL` (см. `src/shared/config/env.ts`). Для UI без бэка есть `VITE_USE_MOCKS`.

## Структура `src/`

```
src/
  app/           # App, router, providers (MAX bridge), global styles
  pages/         # экраны маршрутов (thin): home, new-trip, preferences,
                 # route-loading, ready-route, location-detail, not-found
  features/
    trip-planner/
      api/       # trips, places, SSE stream
      model/     # TripPlannerProvider, types, local packing/budget state
      lib/       # format, cityImage, openingHours
      ui/        # UI по доменам (см. ниже)
  shared/        # config, hooks, api helpers, maplibre/yandex, ui primitives
```

Это FSD-lite: страницы тонкие, бизнес-логика и UI поездки живут в `features/trip-planner`.

### `features/trip-planner/ui`

| Папка      | Что внутри                                                           |
| ---------- | -------------------------------------------------------------------- |
| `shared/`  | Screen, SoftImage, form controls, icons, StatusView, TripActionsMenu |
| `home/`    | HomeTabs, home.module.css                                            |
| `form/`    | City/Date/Time fields, InterestChips, PaceSegment, Stepper           |
| `loading/` | LoadingOrb, ProgressSteps                                            |
| `route/`   | DayTabs, DayRouteMap, CityGuide, ActivityCard, Packing/Budget        |
| `place/`   | PlaceDetails                                                         |
| `nav/`     | BottomNav + helpers deep-link                                        |

Импортируйте публичное API так:

```ts
import { Screen, useTripPlanner, DayRouteMap } from "@/features/trip-planner";
```

CSS-модули при необходимости:

```ts
import styles from "@/features/trip-planner/ui/home/home.module.css";
```

## Основные экраны

1. **Home** — мои поездки / избранное
2. **New trip** — город, даты, бюджет, состав
3. **Preferences** — интересы и темп → старт генерации
4. **Route loading** — SSE-стадии пайплайна
5. **Ready route** — «О поездке», дни, карта, packing, budget
6. **Location detail** — карточка места

### Действия маршрута

Меню `TripActionsMenu` (три точки) — в заголовке готового маршрута и на карточке
поездки на Home. Долгое нажатие на карточку на touch тоже открывает меню.

- **Изменить параметры** — даты, бюджет, состав, интересы и темп (без города:
  смена города = новая поездка); затем повторная генерация.
- **Удалить маршрут** — с подтверждением.

Wizard-форма (`draft`) сбрасывается после успешной генерации и при нажатии
«Новая поездка»; параметры открытого маршрута живут отдельно в
`activeTripDraft` (бюджет и т.п.).

На карточке места в нижней панели остаётся крестик «закрыть» → назад к маршруту.
Изображения через `SoftImage`: skeleton, затем раскрытие сверху вниз. Нижняя
навигация непрозрачная, под ней лёгкий градиент к фону.

## Конфиг

См. `src/shared/config/` — `ROUTES`, env (`VITE_API_BASE_URL`, `VITE_USE_MOCKS`, ключ тайлов Яндекса на этапе сборки).

Полный стенд (web + api + postgres + redis + searxng): корневой `./trip` / README репозитория.
