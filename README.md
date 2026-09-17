# max_hackaton

Мини-приложение (WebApp) для бота в MAX.

## Структура

```text
web/                 # фронт: Vite + React + TypeScript
  src/
    app/             # провайдеры, роутер, глобальные стили
    pages/           # страницы (роуты)
    features/        # бизнес-фичи (FSD-lite)
    shared/          # api, config, hooks, lib, ui, utils, types
```

## Фронт (`web/`)

```bash
cd web
cp .env.example .env.local   # опционально, для API
npm install
npm run dev
```

Сборка:

```bash
cd web
npm run build
npm run preview
```

### Alias

Импорты через `@/` → `src/` (например `@/shared/api`).

### Стек

- Vite + React + TypeScript + React Router
- [`@maxhub/max-ui`](https://www.npmjs.com/package/@maxhub/max-ui)
- [MAX Bridge](https://dev.max.ru/docs/webapps/bridge) → `window.WebApp`
- HTTP-клиент: `shared/api` (`VITE_API_BASE_URL`, опционально `withInitData` для валидации на бэке)

Новые экраны: страница в `pages/` + роут в `app/router/router.tsx`. Логику фичи — в `features/`.

Для продакшена нужен **HTTPS**; URL — в настройках бота на [платформе MAX](https://dev.max.ru/docs/webapps/introduction).
