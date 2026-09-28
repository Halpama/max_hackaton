![2РИСТ](web/public/readme-banner.svg)

# 2РИСТ

Мини-приложение и бот для **MAX**: ИИ собирает маршрут поездки по дням — с картой,  
гидом по городу, сборами и бюджетом.

![Backend tests](https://img.shields.io/badge/pytest-120%20passed-brightgreen?label=backend&color=2f6f4e)![Web tests](https://img.shields.io/badge/vitest-35%20passed-brightgreen?label=web&color=2f6f4e)  
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)![Docker Compose](https://img.shields.io/badge/Docker-compose-blue?logo=docker&logoColor=white)

**Команда:** AI_B2B_SaaS — Шипилов Никита, Гулина Виктория, Кудяева Виктория, Абакаров Арслан  
**Трек:** Досуг и развлечения · **Репозиторий:** [https://github.com/Halpama/max_hackaton](https://github.com/Halpama/max_hackaton)


| Артефакт сдачи      | Путь                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------- |
| OpenAPI 3           | `[openapi.yaml](openapi.yaml)` / `[openapi.json](openapi.json)`                        |
| DATA-API            | `[DATA-API.yaml](DATA-API.yaml)`                                                       |
| Тестовые данные     | `[testdata/](testdata/)`                                                               |
| Зависимости backend | `[backend/requirements.txt](backend/requirements.txt)`                                 |
| Зависимости web     | `[web/package-lock.json](web/package-lock.json)`                                       |
| Env-шаблоны         | `[backend/.env.example](backend/.env.example)`, `[web/.env.example](web/.env.example)` |


Публичный стенд: мини-приложение [https://2-rist.ru](https://2-rist.ru) · API [https://api.2-rist.ru](https://api.2-rist.ru) · Swagger [https://api.2-rist.ru/docs](https://api.2-rist.ru/docs)

---



## Содержание

- [Назначение](#назначение)
- [Основной пользовательский сценарий](#основной-пользовательский-сценарий)
- [Состав и архитектура](#состав-и-архитектура)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Параметры и переменные окружения](#параметры-и-переменные-окружения)
- [Порты](#порты)
- [Зависимости](#зависимости)
- [Внешние сервисы и интеграции](#внешние-сервисы-и-интеграции)
- [Работа с данными](#работа-с-данными)
- [Тестовые данные](#тестовые-данные)
- [Пошаговая проверка](#пошаговая-проверка)
- [Ожидаемое поведение](#ожидаемое-поведение)
- [Известные ограничения](#известные-ограничения)
- [Остановка и повторный запуск](#остановка-и-повторный-запуск)
- [MAX-бот](#max-бот)
- [Собственный API](#собственный-api)

---



## Назначение

**2РИСТ** помогает спланировать короткую поездку по городу РФ: пользователь задаёт город, даты, бюджет и интересы — система собирает маршрут по дням (места, транзит, погода, оценка бюджета, сборы) и отдаёт его в мини-приложении MAX.

## Основной пользовательский сценарий

1. Открыть бота в MAX → `/start` → кнопка **«Открыть планировщик»** (native `open_app`).
2. В WebApp: **Новая поездка** → город, даты/время, бюджет (в т.ч. `0` = только бесплатные места), состав.
3. **Интересы и темп** → запуск генерации.
4. Экран загрузки со live-прогрессом (SSE).
5. Готовый маршрут: дни, карта, «О городе», packing, учёт трат; карточка места → Яндекс.Карты.

Локально без MAX: [http://localhost:3000](http://localhost:3000) (тот же UI, `AUTH_MODE=dev`).

## Состав и архитектура

```text
MAX (бот + WebApp bridge)
        │
        ▼
   web (React SPA, nginx)  ──REST/SSE──►  api (FastAPI)
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                    Postgres 16            Redis 7             SearXNG
                         │
         GigaChat · KudaGo · OpenTripMap · ORS/OSRM · Open-Meteo
```

Подробности и диаграммы: `[ARCHITECTURE.md](ARCHITECTURE.md)`.


| Компонент  | Роль                                                  |
| ---------- | ----------------------------------------------------- |
| `web`      | MAX mini-app (React 19 + Vite), в Docker — nginx      |
| `api`      | FastAPI: поездки, SSE, избранное, бот webhook/polling |
| `postgres` | поездки, места, packing/ledger                        |
| `redis`    | кеш, pub/sub прогресса, rate limit                    |
| `searxng`  | локальный веб-поиск (инфра / digests)                 |




## Быстрый старт (Docker)

Одна команда для всех локальных компонентов:

```bash
cp backend/.env.example backend/.env
# желательно: GIGACHAT_AUTH_KEY, OPENTRIPMAP_API_KEY (см. таблицу ниже)

./trip up          # macOS / Linux / Git Bash / WSL
trip.cmd up        # Windows (Docker Desktop)
```

Эквивалент без CLI: `docker compose up -d --build`.

Миграции Alembic накатываются при старте `api`. Сборка из исходников рассчитана на ≤ 5 минут (без первичной загрузки базовых образов).


| Команда             | Действие                              |
| ------------------- | ------------------------------------- |
| `./trip up`         | поднять стек, дождаться healthy       |
| `./trip status`     | здоровье сервисов и ключей            |
| `./trip doctor`     | Docker, порты, `.env`                 |
| `./trip open`       | открыть фронт и Swagger               |
| `./trip bot on`     | включить MAX-бота (нужен токен)       |
| `./trip down`       | остановить и убрать контейнеры        |
| `./trip restart`    | перезапуск api (бот подхватит конфиг) |
| `./trip logs [svc]` | логи                                  |




## Параметры и переменные окружения

Полные шаблоны **без секретов**: `[backend/.env.example](backend/.env.example)`, `[web/.env.example](web/.env.example)`.

### Обязательные для полноценной генерации маршрута


| Переменная            | Где взять        | Без ключа                                               |
| --------------------- | ---------------- | ------------------------------------------------------- |
| `GIGACHAT_AUTH_KEY`   | кабинет GigaChat | LLM-стадии на fallback (город as-is, отбор по рейтингу) |
| `OPENTRIPMAP_API_KEY` | OpenTripMap      | вне 12 городов KudaGo поиск мест деградирует            |




### Рекомендуемые


| Переменная              | Назначение                                                                                          |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| `ORS_API_KEY`           | маршрутизация; иначе публичный OSRM                                                                 |
| `MAX_BOT_TOKEN`         | бот MAX; без токена мини-app всё равно открывается по URL                                           |
| `MAX_BOT_ENABLED=true`  | включить бота (`./trip bot on`)                                                                     |
| `AUTH_MODE=dev` | `max` | `dev` — без подписи initData (локалка/жюри Docker); `max` — проверка подписи + свежесть `auth_date` |
| `VITE_API_BASE_URL`     | в Docker-образе web задаётся на API; локальный Vite проксирует `/api`                               |


Остальные флаги (`KUDAGO_ENABLED`, `WEATHER_ENABLED`, `SEARXNG_*`, rate limit, ML-классификатор среды) — в `.env.example` с комментариями.

**Секреты для жюри** (токены/ключи стенда) передаются отдельно с 1-го слайда презентации / канала команды — в git не кладутся.

## Порты


| Сервис     | Хост                                                                               |
| ---------- | ---------------------------------------------------------------------------------- |
| Фронт      | [http://localhost:3000](http://localhost:3000)                                     |
| API        | [http://localhost:8000](http://localhost:8000)                                     |
| Swagger    | [http://localhost:8000/docs](http://localhost:8000/docs)                           |
| Bot status | [http://localhost:8000/api/v1/bot/status](http://localhost:8000/api/v1/bot/status) |
| SearXNG    | [http://127.0.0.1:8081](http://127.0.0.1:8081) (только localhost)                  |
| Postgres   | `localhost:5433` → внутри `postgres:5432`                                          |
| Redis      | `localhost:6379`                                                                   |




## Зависимости


| Стек                   | Фиксация версий                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| Backend (Python 3.12+) | `[backend/requirements.txt](backend/requirements.txt)` + `[backend/pyproject.toml](backend/pyproject.toml)` |
| Web (Node 22)          | `[web/package-lock.json](web/package-lock.json)` + `[web/package.json](web/package.json)`                   |


Docker-образы ставят зависимости из этих файлов при `docker compose build`.

## Внешние сервисы и интеграции


| Сервис                  | Ключ                              | Что даёт                                | Воспроизводимость в Docker         |
| ----------------------- | --------------------------------- | --------------------------------------- | ---------------------------------- |
| **MAX Bot API**         | `MAX_BOT_TOKEN`                   | чат, `open_app`, webhook/polling        | снаружи (platform-api2.max.ru)     |
| **MAX WebApp bridge**   | —                                 | `initData`, BackButton, `openLink`      | CDN `st.max.ru` в `web/index.html` |
| GigaChat                | `GIGACHAT_AUTH_KEY`               | нормализация города, отбор мест         | снаружи                            |
| OpenTripMap             | `OPENTRIPMAP_API_KEY`             | пул мест                                | снаружи                            |
| KudaGo                  | нет                               | часы, популярность, тексты (12 городов) | снаружи                            |
| openrouteservice / OSRM | `ORS_API_KEY` опц.                | время в пути                            | снаружи                            |
| Open-Meteo              | нет                               | геокодинг RU + погода 16 дней           | снаружи                            |
| SearXNG                 | нет                               | digests / demo tools                    | **внутри** compose                 |
| Яндекс.Карты (тайлы)    | опц. `VITE_YANDEX_MAPS_TILES_KEY` | подложка карты                          | снаружи; иначе OSM                 |


Без GigaChat/OTM стек **поднимается**; генерация в KudaGo-городах частично работает, вне них — с деградацией (см. ограничения).

## Работа с данными

- **Живые каталоги:** KudaGo (атрибуция `sourceUrl` / `sourceName` на карточке), OpenTripMap.
- **Оценки:** цены мест помечены `priceEstimated: true` (UI — «Оценка»); исключение — явно бесплатный вход.
- **Погода:** Open-Meteo; дни дальше 16-дневного горизонта — без прогноза.
- **Кеш:** Redis (TTL на ответы провайдеров); прогресс генерации — Redis pub/sub.
- **Персональные данные:** `max_user_id` из initData; в `AUTH_MODE=dev` — фиксированный `DEV_USER_ID`.
- **ML environment model** (`*.joblib`) **не в git** — на стенде кладётся отдельно; без файла классификатор деградирует к правилам (`ENVIRONMENT_MODEL_MODE`).

Мок-режим фронта: `VITE_USE_MOCKS=true` — UI на встроенном mock-маршруте без API.

## Тестовые данные


| Файл                                                                           | Назначение                |
| ------------------------------------------------------------------------------ | ------------------------- |
| `[testdata/trip_draft_kazan.json](testdata/trip_draft_kazan.json)`             | тело `POST /api/v1/trips` |
| `[testdata/trip_draft_free_budget.json](testdata/trip_draft_free_budget.json)` | бюджет `0`                |


Порядок работы — `[testdata/README.md](testdata/README.md)`. Контракт проверок API — `[DATA-API.yaml](DATA-API.yaml)`.

## Пошаговая проверка



### A. Локально (Docker, без MAX)

1. `cp backend/.env.example backend/.env` и при наличии вписать ключи.
2. `./trip up` → дождаться healthy (`./trip status`).
3. Открыть [http://localhost:3000](http://localhost:3000) → создать поездку (Казань, 1–2 дня) → дождаться маршрута.
4. API: `curl -s http://localhost:8000/health` → `"status":"ok"`.
5. `curl -sS -X POST http://localhost:8000/api/v1/trips -H 'Content-Type: application/json' -d @testdata/trip_draft_kazan.json` → `202` + `id`.
6. `curl -N http://localhost:8000/api/v1/trips/<id>/stream` → события `stage` / `done`.
7. Тесты: `docker compose exec api pytest -q`.



### B. В MAX (основной сценарий)

1. В кабинете MAX: токен бота, URL мини-приложения → `https://2-rist.ru` (или ваш стенд).
2. В `backend/.env`: `MAX_BOT_TOKEN=…`, `MAX_BOT_ENABLED=true`, на проде `AUTH_MODE=max`.
3. `./trip bot on` (или деплой стенда) → в чате бота `/start` → **Открыть планировщик**.
4. Пройти сценарий из раздела выше на телефоне и в веб-клиенте MAX.
5. Диагностика: `GET /api/v1/bot/status` → `enabled`, `configured`, при токене — `username` / deeplink.



### Автопроверка качества

```bash
docker compose exec api pytest -q
cd backend && .venv/bin/python scripts/smoke.py --base-url http://localhost:8000
cd backend && .venv/bin/python scripts/audit.py
cd web && npm ci && npm run lint && npm run build
```



## Ожидаемое поведение


| Действие                           | Результат                                                                     |
| ---------------------------------- | ----------------------------------------------------------------------------- |
| `POST /api/v1/trips`               | `202` + `id`, статус `pending`/`running`                                      |
| SSE `/trips/{id}/stream`           | стадии `analyze` → `places` → `transit` → `budget` → `schedule`, затем `done` |
| `GET /trips/{id}` после готовности | `status: ready`, объект `route` с днями и местами                             |
| Бюджет `0`                         | в маршруте только бесплатные места, лейбл `0 ₽`                               |
| `/start` в боте                    | текст + клавиатура с `open_app`                                               |
| Без `GIGACHAT_AUTH_KEY`            | генерация не падает, отбор упрощён                                            |
| Rate limit                         | при превышении `429` + `code: rate_limited`                                   |




## Известные ограничения

- KudaGo покрывает 12 городов; остальные опираются на OpenTripMap (нужен ключ).
- Цены входа — оценка, не прайс площадки (`priceEstimated`).
- Погода только в пределах ~16 дней от «сегодня».
- Жильё (`findHousing`) в MVP не бронируется — параметр формы зарезервирован.
- `environment_model.joblib` не хранится в git — без артефакта на сервере режим ML ограничен.
- Уведомления в чат MAX о завершении генерации не отправляются — результат в WebApp.
- SearXNG tool-loop GigaChat в пятистадийный пайплайн полностью не встроен (digests — да).



## Остановка и повторный запуск

```bash
./trip down       # остановить и удалить контейнеры стека
./trip up         # поднять заново (данные Postgres в volume сохраняются)
./trip restart    # быстрый перезапуск api после правки .env
docker compose down -v   # полный сброс volume (БД очистится)
```



## MAX-бот

Интеграция **полная на уровне MVP**: Bot API-клиент (`platform-api2.max.ru`), команды `/start` `/help` `/about`, native `open_app`, webhook **или** long polling, WebApp bridge (`ready`, `initData` → `Authorization: tma …`, BackButton, `openLink`), проверка подписи и срока `auth_date` при `AUTH_MODE=max`, deep-link `start_param` → `/trips/new`.

По умолчанию бот **выключен** (`MAX_BOT_ENABLED=false`). Включение: токен в `.env` → `./trip bot on`.  
Подробнее: `[backend/README.md](backend/README.md#max-бот)`.

## Собственный API


|              |                                                                                      |
| ------------ | ------------------------------------------------------------------------------------ |
| Base (стенд) | `https://api.2-rist.ru`                                                              |
| OpenAPI      | `[openapi.yaml](openapi.yaml)`                                                       |
| DATA-API     | `[DATA-API.yaml](DATA-API.yaml)`                                                     |
| Swagger UI   | `/docs`                                                                              |
| Учётки       | отдельного логина/пароля нет: идентификация через MAX `initData` или `AUTH_MODE=dev` |


Основные методы: `POST/GET /api/v1/trips`, `GET /api/v1/trips/{id}/stream`, places, favorites, trip state/ledger, `GET /api/v1/geo/cities`, bot status/webhook.
