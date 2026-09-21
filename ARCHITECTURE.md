# Архитектура Trip Planner

Мини-приложение для MAX: пользователь задаёт город, даты и интересы → бэкенд
собирает маршрут по дням и стримит прогресс по SSE → фронт показывает план,
карту, бюджет и сборы.

---

## Общая схема

```mermaid
flowchart TB
  subgraph Client["Клиент"]
    MAX["MAX WebApp / браузер"]
    WEB["web — React SPA<br/>Vite + nginx"]
  end

  subgraph Compose["docker-compose"]
    API["api — FastAPI"]
    PG[(Postgres)]
    RD[(Redis)]
  end

  subgraph External["Внешние API"]
    GC[GigaChat]
    OTM[OpenTripMap]
    KD[KudaGo]
    ORS[openrouteservice / OSRM]
    WM[Open-Meteo]
    WP[Wikipedia]
  end

  MAX --> WEB
  WEB -->|"REST + SSE"| API
  API --> PG
  API --> RD
  API --> GC & OTM & KD & ORS & WM
  WEB -.->|"превью городов"| WP
```

| Контейнер | Роль |
| --------- | ---- |
| `web` | собранный SPA за nginx |
| `api` | FastAPI, миграции Alembic, uvicorn |
| `postgres` | поездки, места, избранное, ledger |
| `redis` | кеш внешних ответов, pub/sub прогресса SSE, квоты |

---

## Модули бэкенда

```mermaid
flowchart LR
  subgraph Entry
    MAIN[main.py]
    BOT[bot/]
  end

  subgraph API["api/"]
    V1["v1/trips · places<br/>favorites · trip_state"]
    DEPS[deps — auth]
  end

  subgraph Services["services/"]
    PIPE[pipeline]
    PL[places]
    LLM[llm]
    TR[transit]
    BD[budget]
    SCH[scheduler]
    PR[progress]
    FMT[formatting]
  end

  subgraph Clients["clients/"]
    C_GC[gigachat]
    C_OTM[opentripmap]
    C_KD[kudago]
    C_ORS[osrm + ORS]
    C_WX[weather]
  end

  subgraph Infra
    CACHE[cache/ Redis]
    DB[db/ SQLAlchemy]
    CORE[core/ config · security · errors]
    SCHEMAS[schemas/ Pydantic]
  end

  MAIN --> V1
  MAIN --> BOT
  V1 --> DEPS
  V1 --> PIPE
  V1 --> DB
  PIPE --> PL & LLM & TR & BD & SCH & PR & FMT
  PL --> C_OTM & C_KD
  LLM --> C_GC
  TR --> C_ORS
  PIPE --> C_WX
  Clients --> CACHE
  PIPE --> CACHE
  PIPE --> DB
  V1 --> SCHEMAS
  DEPS --> CORE
```

### Назначение модулей

| Модуль | Что делает |
| ------ | ---------- |
| `app/main.py` | lifespan, CORS, роутеры, health |
| `app/api/v1/` | HTTP: создание поездки, SSE-стрим, места, избранное, локальный state |
| `app/api/deps.py` | пользователь из MAX `initData` (или `AUTH_MODE=dev`) |
| `app/services/pipeline.py` | оркестратор 5 стадий генерации маршрута |
| `app/services/places.py` | кандидаты: KudaGo → OpenTripMap, дедуп, категории |
| `app/services/llm.py` | нормализация города и отбор мест через GigaChat |
| `app/services/scheduler.py` | раскладка мест по дням с учётом темпа |
| `app/services/transit.py` | ноги между точками, режим пешком/метро/такси |
| `app/services/budget.py` | оценка цен + флаг `priceEstimated` |
| `app/services/progress.py` | публикация стадий в Redis pub/sub |
| `app/clients/*` | HTTP-клиенты внешних API |
| `app/cache/` | ключи, TTL, декоратор `cached_json`, квота OTM |
| `app/db/` | модели, сессия, репозитории |
| `app/schemas/` | контракт с фронтом (camelCase) |
| `app/bot/` | MAX-бот: platform-api2 client, open_app, webhook / long polling |
| `app/core/` | настройки, логирование, ошибки, security |

---

## Пайплайн генерации маршрута

Стадии совпадают с `LOADING_STEPS` на фронте и стримятся по SSE.

```mermaid
sequenceDiagram
  participant UI as web
  participant API as FastAPI
  participant R as Redis
  participant S as pipeline
  participant Ext as Внешние API

  UI->>API: POST /api/v1/trips
  API-->>UI: 202 { id, status: pending }
  API->>S: generate_trip (background)

  UI->>API: GET /trips/{id}/stream (SSE)
  API->>R: SUBSCRIBE trip:{id}:progress

  S->>R: stage analyze
  S->>Ext: GigaChat — город / радиус
  S->>R: stage places
  S->>Ext: KudaGo + OpenTripMap
  S->>Ext: GigaChat — курация
  S->>R: stage transit
  S->>Ext: ORS / OSRM
  S->>R: stage budget
  S->>R: stage schedule
  S->>Ext: Open-Meteo (если даты в горизонте)
  S->>API: persist RoutePlan → Postgres
  S->>R: event done
  R-->>UI: SSE done + route
```

```mermaid
flowchart TD
  A[analyze] --> B[places]
  B --> C[transit]
  C --> D[budget]
  D --> E[schedule]
  E --> F[RoutePlan]

  A -.- A1[GigaChat: city, radius]
  B -.- B1[KudaGo / OTM + LLM curate]
  C -.- C1[ORS matrix/legs]
  D -.- D1[оценка цен]
  E -.- E1[дни + погода + Place map]
```

---

## Модули фронтенда

Feature-Sliced-подобная раскладка: экраны тонкие, логика в `features/trip-planner`.

```mermaid
flowchart TB
  subgraph App["app/"]
    PROVIDERS[providers — MAX bridge]
    ROUTER[router — AppShell, scroll]
    STYLES[styles]
  end

  subgraph Pages["pages/"]
    HOME[home]
    NEW[new-trip]
    PREF[preferences]
    LOAD[route-loading]
    ROUTE[ready-route]
    PLACE[location-detail]
  end

  subgraph Feature["features/trip-planner/"]
    UI[ui — экраны-виджеты]
    MODEL[model — TripPlannerProvider]
    FAPI[api — trips / places / state]
    LIB[lib — openingHours, cityImage]
  end

  subgraph Shared["shared/"]
    HTTP[api — fetch + SSE]
    CFG[config — routes, env]
    MAXLIB[lib/max — WebApp]
    MAP[lib/maplibre]
  end

  PROVIDERS --> Pages
  ROUTER --> Pages
  Pages --> Feature
  Feature --> Shared
  FAPI --> HTTP
  MODEL --> FAPI
  UI --> MODEL
```

### Экраны → ответственность

| Страница | Модуль | Роль |
| -------- | ------ | ---- |
| `/` | `pages/home` | список поездок + избранное |
| `/trips/new` | `pages/new-trip` | черновик: город, даты, бюджет |
| `/preferences` | `pages/preferences` | интересы, темп → `POST /trips` |
| `/loading` | `pages/route-loading` | SSE-прогресс генерации |
| `/route` | `pages/ready-route` | дни, карта, сборы, бюджет |
| `/places/:id` | `pages/location-detail` | карточка места |

### Внутри `features/trip-planner`

| Слой | Примеры | Роль |
| ---- | ------- | ---- |
| `model/` | `TripPlannerProvider`, `types`, `useTripLocalState` | глобальный стейт поездки + локальный packing/ledger |
| `api/` | `trips.ts`, `places.ts`, `state.ts` | типизированные вызовы бэка |
| `ui/` | `DayTabs`, `DayWeatherBadge`, `PlaceDetails`, `SoftImage`… | переиспользуемые виджеты |
| `lib/` | `openingHours`, `cityImage`, `format` | чистые хелперы без React |

---

## Данные и кеш

```mermaid
flowchart LR
  subgraph Persist["Postgres"]
    U[users]
    T[trips + route_plan JSON]
    P[places]
    F[favorites]
    L[ledger / packing state]
  end

  subgraph Cache["Redis"]
    K1[otm:* · kudago:*]
    K2[osrm:* · weather:*]
    K3[gigachat:* · trip:plan:*]
    K4[trip:{id}:progress / events]
    K5[otm:quota:YYYY-MM-DD]
  end

  API[FastAPI] --> Persist
  API --> Cache
```

Ответы внешних API кешируются с длинными TTL, чтобы не жечь бесплатные квоты.
Прогресс генерации живёт в pub/sub + replay-логе, чтобы поздний SSE-подписчик
всё равно увидел стадии.

---

## Источники данных (обогащение)

```mermaid
flowchart TB
  CITY{Город в каталоге KudaGo?}
  CITY -->|да| KD[KudaGo<br/>часы · популярность · описания]
  CITY -->|нет / мало| OTM[OpenTripMap<br/>базовый POI-слой]
  KD --> MERGE[merge + dedupe]
  OTM --> MERGE
  MERGE --> LLM[GigaChat curate]
  LLM --> PLAN[RoutePlan]

  PLAN --> WX{Дата ≤ 16 дней?}
  WX -->|да| OM[Open-Meteo]
  WX -->|нет| NA[weather: null]
```

| Источник | Ключ | Роль |
| -------- | ---- | ---- |
| KudaGo | нет | приоритет для 12 городов |
| OpenTripMap | да | фолбэк / дополнение |
| GigaChat | да | город + отбор мест |
| openrouteservice | да | время в пути (фолбэк OSRM) |
| Open-Meteo | нет | погода по дням |
| Wikipedia | нет | превью города на главной (клиент) |

---

## Контракт API (кратко)

```text
POST   /api/v1/trips                 создать задачу генерации
GET    /api/v1/trips                 список поездок пользователя
GET    /api/v1/trips/{id}            статус + RoutePlan
GET    /api/v1/trips/{id}/stream     SSE: stage | done | error
POST   /api/v1/trips/{id}/retry      перезапуск
GET    /api/v1/places/{id}           карточка места
GET/POST/DELETE /api/v1/favorites   избранное
GET/PUT /api/v1/trips/{id}/state     packing + ledger
```

Схемы — `backend/app/schemas/trip.py`, зеркалят `web/.../model/types.ts`
(сериализация camelCase).
