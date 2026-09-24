# Feature modules

Сюда кладём бизнес-фичи (FSD-lite). Сейчас: `trip-planner`.

## `trip-planner`

| Слой | Назначение |
| --- | --- |
| `api/` | HTTP/SSE к бэкенду поездок |
| `model/` | типы, провайдер, локальный стейт (packing/budget) |
| `lib/` | форматтеры, city images, opening hours |
| `ui/` | UI-компоненты фичи, разложены по доменам |

### `ui/` по папкам

- `shared/` — Screen, SoftImage, FormControls, icons, StatusView, badges
- `home/` — табы и стили домашнего экрана
- `form/` — поля создания поездки (город, даты, интересы, темп)
- `loading/` — орб и шаги генерации
- `route/` — готовый маршрут: дни, карта, гайд, packing/budget
- `place/` — карточка места
- `nav/` — нижняя навигация и trip deep-link helpers

Публичный API фичи — через `@/features/trip-planner` (barrel `index.ts`).
Deep-импорты CSS допустимы: `@/features/trip-planner/ui/<domain>/*.module.css`.
