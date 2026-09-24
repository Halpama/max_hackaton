<p align="center">
  <img src="web/public/readme-banner.svg" alt="2РИСТ" width="100%" />
</p>

<h1 align="center">2РИСТ</h1>

<p align="center">
  Мини-приложение и бот для <b>MAX</b>: ИИ собирает маршрут поездки по дням — с картой,<br/>
  гидом по городу, сборами и бюджетом.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/pytest-120%20passed-brightgreen?label=backend&color=2f6f4e" alt="Backend tests: 120 passed" />
  <img src="https://img.shields.io/badge/vitest-35%20passed-brightgreen?label=web&color=2f6f4e" alt="Web tests: 35 passed" />
  <br/>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/Node-22-5FA04E?logo=nodedotjs&logoColor=white" alt="Node 22" />
  <br/>
  <img src="https://img.shields.io/badge/Postgres-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Docker-compose-blue?logo=docker&logoColor=white" alt="Docker Compose" />
  <img src="https://img.shields.io/badge/%D0%A1%D1%82%D0%B5%D0%BA-GigaChat%20%C2%B7%20SearXNG%20%C2%B7%20KudaGo-6b57ff" alt="Stack: GigaChat, SearXNG, KudaGo" />
</p>

## Содержание

- [Возможности](#возможности)
- [Быстрый старт](#быстрый-старт)
  - [MAX-бот](#max-бот)
- [Поток экранов](#поток-экранов)
- [Структура](#структура)
- [Проверка](#проверка)

## Возможности

- Бот MAX → кнопка «Открыть планировщик» → WebApp
- Генерация маршрута по интересам, темпу и бюджету (в т.ч. `0 ₽`)
- План по дням, карта, вкладка «О городе», packing и учёт трат
- Live-прогресс по SSE, память по местам/городам, локальный SearXNG

## Быстрый старт

```bash
cp backend/.env.example backend/.env
# GIGACHAT_AUTH_KEY, OPENTRIPMAP_API_KEY (опционально ORS / MAX_BOT_TOKEN)

./trip up          # macOS / Linux / Git Bash / WSL
trip.cmd up        # Windows (Docker Desktop)
```

| Команда | Действие |
| ------- | -------- |
| `./trip up` | поднять стек, дождаться healthy |
| `./trip status` | здоровье сервисов и ключей |
| `./trip bot on` | включить MAX-бота |
| `./trip doctor` | Docker, порты, `.env` |
| `./trip open` | открыть фронт и Swagger |

| Сервис | Адрес |
| ------ | ----- |
| Фронт | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Бот | http://localhost:8000/api/v1/bot/status |
| SearXNG | http://127.0.0.1:8081 |
| Postgres / Redis | `localhost:5433` / `localhost:6379` |

Миграции накатываются при старте. Без CLI: `docker compose up -d --build`.

### MAX-бот

По умолчанию выключен. Для демо: `MAX_BOT_TOKEN` в `backend/.env` → `./trip bot on` → в чате `/start` → «Открыть планировщик».  
Режим: webhook, если задан `MAX_BOT_WEBHOOK_URL`, иначе long polling. Подробнее — [backend/README.md](backend/README.md#max-бот).

## Поток экранов

1. `/` — поездки и избранное  
2. `/trips/new` — город, даты, бюджет, состав  
3. `/preferences` — интересы и темп  
4. `/loading` — SSE-прогресс генерации  
5. `/route` — дни, карта, сборы, бюджет  
6. `/places/:id` — карточка места → Яндекс.Карты  

## Структура

```text
trip / trip.cmd      # CLI для жюри
backend/             # FastAPI, пайплайн, бот, клиенты API
web/                 # MAX WebApp (React)
infra/searxng/       # конфиг SearXNG
docker-compose.yml   # web + api + postgres + redis + searxng
```

## Проверка

```bash
docker compose exec api pytest -q
cd backend && .venv/bin/python scripts/smoke.py
cd backend && .venv/bin/python scripts/audit.py
cd web && npm run lint && npm run build
```

`smoke` — сквозной прогон на ключах, `audit` — качество маршрутов (дубли, часы работы, метро, бюджет дня).
