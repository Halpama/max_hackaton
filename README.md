# max_hackaton

Мини-приложение Trip Planner для бота в MAX. Бэкенд (Python) — отдельно.

## Структура

```text
web/src/
  app/                    # провайдеры, роутер, стили
  pages/                  # экраны
  features/trip-planner/  # UI, mock, состояние
  shared/                 # api, config, hooks, lib
```

## Запуск

```bash
cd web
npm install
npm run dev
```

### Поток экранов (мок)

1. `/` — главная: табы **Поездки** / **Избранное** (поиск + фильтр по городам)
2. `/trips/new` — новая поездка
3. `/preferences` — интересы и темп
4. `/loading` — ИИ собирает маршрут
5. `/route` — план по дням + **превью карты** с точками
6. `/places/:placeId` — карточка места

Макет: `web/layout.pen`.
