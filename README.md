# max_hackaton

Trip Planner — мини-приложение для бота в MAX: ИИ собирает маршрут поездки по
дням с учётом интересов, темпа и бюджета.

## Быстрый старт (для жюри)

```bash
cp backend/.env.example backend/.env   # если ещё нет
# впиши GIGACHAT_AUTH_KEY и OPENTRIPMAP_API_KEY (опционально ORS / MAX_BOT_TOKEN)

# macOS / Linux / Git Bash / WSL
./trip up

# Windows (cmd / PowerShell) — тот же CLI
trip.cmd up
```

| Команда | Что делает |
| ------- | ---------- |
| `./trip up` / `trip.cmd up` | docker compose up --build, ждёт healthy, печатает статус |
| `./trip status` / `trip.cmd status` | postgres/redis/api/web + GigaChat/OTM/ORS/KudaGo/погода/бот |
| `./trip bot on` / `trip.cmd bot on` | `MAX_BOT_ENABLED=true` + restart api (нужен токен) |
| `./trip bot mode polling` | long polling без HTTPS-туннеля |
| `./trip doctor` | проверка Docker, портов и ключей в `.env` |
| `./trip open` | открыть фронт и Swagger |

На Windows нужен только **Docker Desktop** (в комплекте `docker compose` и `curl`). Bash не обязателен — используй `trip.cmd`. Git Bash / WSL могут запускать `./trip` как на Mac.

| Сервис   | Адрес                      |
| -------- | -------------------------- |
| Фронт    | http://localhost:3000      |
| API      | http://localhost:8000      |
| Swagger  | http://localhost:8000/docs |
| Bot      | http://localhost:8000/api/v1/bot/status |
| SearXNG  | http://127.0.0.1:8081 (только localhost) |
| Postgres | localhost:5433             |
| Redis    | localhost:6379             |

Миграции накатываются сами. Эквивалент без CLI: `docker compose up -d --build`.

### MAX-бот

По умолчанию выключен (`MAX_BOT_ENABLED=false`). Для демо:

1. Токен из кабинета MAX → `MAX_BOT_TOKEN` в `backend/.env`
2. `./trip bot on` — API сам выберет режим: **webhook**, если задан
   `MAX_BOT_WEBHOOK_URL`, иначе **long polling**
3. В чате с ботом: `/start` → кнопка «Открыть планировщик» (`open_app`)

Подробности — в [backend/README.md](backend/README.md#max-бот).

## Структура

```text
trip / trip.cmd           # CLI для жюри (Unix / Windows)
backend/                  # FastAPI + Redis + Postgres
  app/clients/            # GigaChat, OTM, KudaGo, ORS, Open-Meteo, SearXNG
  app/services/           # пайплайн генерации из 5 стадий
  app/api/v1/             # ручки, включая SSE и geo/cities
  app/bot/                # MAX-бот: client, handlers, webhook, polling
infra/searxng/            # settings.yml для локального SearXNG
web/src/
  app/                    # провайдеры, роутер, стили
  pages/                  # экраны
  features/trip-planner/  # UI, состояние, вызовы API
  shared/                 # api-клиент, SSE, config, maplibre, yandex
docker-compose.yml        # web + api + postgres + redis + searxng
```

Диаграммы модулей и потоков — в [ARCHITECTURE.md](ARCHITECTURE.md).

Порт фронта и адрес API: `WEB_PORT` / `WEB_API_BASE_URL` (после смены —
`docker compose build web`). Для hot reload фронта:

```bash
./trip up                  # или только: docker compose up -d api
cd web && npm install && npm run dev
```

Фронт на `http://localhost:5173`, моки: `VITE_USE_MOCKS=true`.

### С iPhone в той же Wi‑Fi

1. Подними API (`./trip up` или только `docker compose up -d api`)
2. `cd web && npm run dev` — в терминале будет **Network** URL вида `http://192.168.x.x:5173`
3. Открой этот URL в Safari на айфоне

`VITE_API_BASE_URL` можно оставить пустым: запросы идут на тот же хост, Vite проксирует `/api` на бэкенд.

Подробности по API, кешу, боту и авторизации — в [backend/README.md](backend/README.md).

## Поток экранов

1. `/` — главная: табы **Поездки** / **Избранное**
2. `/trips/new` — город, даты (≥ сегодня), бюджет (`0 ₽` = бесплатные места), число путешественников
3. `/preferences` — интересы и темп
4. `/loading` — SSE-прогресс; при ошибке — retry или на главную
5. `/route?tripId=…&day=…` — план по дням, карта, сборы и бюджет
6. `/places/:placeId` — карточка места; «На карте» открывает пин в Яндекс.Картах

Макет: `web/layout.pen`.

## Проверка

```bash
docker compose exec api pytest -q                      # тесты бэкенда
cd backend && .venv/bin/python scripts/smoke.py        # сквозной прогон на реальных ключах
cd backend && .venv/bin/python scripts/audit.py        # качество маршрутов по пяти городам
cd web && npm run lint && npm run build                # фронт
```

`audit.py` проверяет не проводку, а содержимое: нет ли дублей одного и того же
объекта, не продаётся ли билет на открытую площадь, помещается ли день в
интервал прибытия и отъезда, не предлагается ли метро там, где его нет.
