# max_hackaton

Мини-приложение Trip Planner для бота в MAX. Бэкенд (Python) — отдельно.

## Структура

```text
web/src/
  app/                 # провайдеры, роутер, стили
  pages/               # экраны: new-trip → preferences → loading → route → place
  features/trip-planner/  # UI, mock-данные, состояние черновика
  shared/              # api, config, hooks, lib
```

## Запуск

```bash
cd web
npm install
npm run dev
```

### Поток экранов (мок)

1. `/` — новая поездка  
2. `/preferences` — интересы и темп  
3. `/loading` — ИИ собирает маршрут  
4. `/route` — готовый план по дням  
5. `/places/:placeId` — карточка места  

Состояние черновика держится в `TripPlannerProvider` без бэкенда
