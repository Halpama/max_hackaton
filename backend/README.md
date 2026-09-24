# 2РИСТ backend

FastAPI + Redis + Postgres. Собирает маршрут поездки из OpenTripMap и GigaChat
и отдаёт прогресс по SSE.

## Запуск

```bash
# из корня репозитория
cp backend/.env.example backend/.env   # если .env ещё нет
# впиши GIGACHAT_AUTH_KEY и OPENTRIPMAP_API_KEY в backend/.env
docker compose up -d --build api       # postgres и redis подтянутся сами
curl http://localhost:8000/health
```

`docker compose up -d --build` без аргументов поднимает ещё и фронт на
http://localhost:3000.

Доступно:

| Сервис   | Адрес                              |
| -------- | ---------------------------------- |
| API      | http://localhost:8000              |
| Swagger  | http://localhost:8000/docs         |
| Postgres | localhost:5433 (внутри — postgres:5432) |
| Redis    | localhost:6379                     |

Миграции Alembic накатываются автоматически при старте контейнера.

## Проверка

```bash
# юнит- и интеграционные тесты (внешние API замоканы, Redis и БД поддельные)
docker compose exec api pytest -q

# полный прогон с реальными ключами: генерация маршрута + все ручки
docker compose exec api python scripts/smoke.py --base-url http://localhost:8000
# или с хоста
cd backend && .venv/bin/python scripts/smoke.py --city Казань

# качество маршрутов: пять городов, разные темп, бюджет и состав интересов
cd backend && .venv/bin/python scripts/audit.py
cd backend && .venv/bin/python scripts/audit.py --scenario spb --verbose

# прогон пайплайна на реальных Postgres и Redis, но с заглушками провайдеров
docker compose exec -e OPENTRIPMAP_API_KEY=stub api python scripts/offline_e2e.py
```

`smoke.py` отвечает на вопрос «работает ли проводка», `audit.py` — «осмысленный
ли получился маршрут»: дубликаты одного объекта, билет на открытую площадь,
день, вылезающий за время отъезда, метро в городе без метро, пустой день,
перекос по загрузке дней, отсутствие фотографий и описаний.

`offline_e2e.py` отвечает на третий вопрос — доходит ли прогресс между
процессами: он публикует стадии из отдельного процесса, а SSE-ручка в контейнере
их отдаёт. Заглушки пишутся в те же ключи кеша, что и настоящие провайдеры,
поэтому скрипт подчищает их за собой на выходе.

## API

| Метод  | Путь                                  | Назначение                                   |
| ------ | ------------------------------------- | -------------------------------------------- |
| POST   | `/api/v1/trips`                       | создать поездку, вернуть `id` (202)           |
| GET    | `/api/v1/trips/{id}/stream`           | SSE: `stage`, `done`, `error`                 |
| GET    | `/api/v1/trips/{id}`                  | статус + готовый `RoutePlan`                  |
| GET    | `/api/v1/trips`                       | список поездок для главной                    |
| DELETE | `/api/v1/trips/{id}`                  | архивировать поездку (soft-hide)              |
| POST   | `/api/v1/trips/{id}/retry`            | перезапустить упавшую генерацию               |
| GET    | `/api/v1/places/{id}`                 | карточка места                                |
| GET    | `/api/v1/favorites`                   | избранные места                               |
| PUT    | `/api/v1/favorites/{placeId}`         | добавить в избранное                          |
| DELETE | `/api/v1/favorites/{placeId}`         | убрать из избранного                          |
| GET    | `/api/v1/trips/{id}/state`            | блоки сборов                                  |
| PUT    | `/api/v1/trips/{id}/state`            | сохранить блоки сборов                        |
| GET    | `/api/v1/trips/{id}/ledger`           | траты и пополнения                            |
| POST   | `/api/v1/trips/{id}/ledger`           | добавить запись                               |
| DELETE | `/api/v1/trips/{id}/ledger/{entryId}` | удалить запись                                |
| GET    | `/api/v1/geo/cities`                  | автокомплит городов (Open-Meteo, только RU)   |
| GET    | `/api/v1/bot/status`                  | конфиг бота + `/me` (если токен есть)         |
| POST   | `/api/v1/bot/invite`                  | клавиатура-инвайт (в prod — с секретом)       |
| POST   | `/api/v1/bot/webhook`                 | вебхук MAX (secret в `X-Max-Bot-Api-Secret`)  |

Лимиты: `/api/v1` закрыт fixed-window rate limit на Redis (глобально 120/мин,
`POST /trips` — 10/мин, `geo/cities` — 30/мин, вебхук бота не лимитируется;
`RATE_LIMIT_*` в `.env.example`). Превышение — `429` с `code: "rate_limited"`.

## Как собирается маршрут

Пять стадий, их ключи совпадают с `LOADING_STEPS` на фронте, поэтому экран
загрузки двигается по реальному прогрессу, а не по таймеру.

1. `analyze` — GigaChat нормализует город и выбирает радиус поиска.
2. `places` — центр города через Open-Meteo Geocoding (`countryCode=RU`, bbox
   России); затем KudaGo и/или OpenTripMap → GigaChat отбирает места.
   При `budget = 0` в пул попадают только бесплатные кандидаты.
3. `transit` — openrouteservice (или OSRM) считает время между точками,
   выбирается пешком / метро / такси.
4. `budget` — при `budget > 0` цены масштабируются под бюджет; при `0`
   везде «Бесплатно», лейбл поездки `0 ₽`.
5. `schedule` — дни, время визитов, погода на каждый день, итоговый `RoutePlan`.

Прогресс публикуется в Redis pub/sub `trip:{id}:progress`, SSE-ручка на него
подписана — стрим работает и при нескольких воркерах uvicorn.

Каждый шаг деградирует, а не падает: без `GIGACHAT_AUTH_KEY` город берётся как
есть и места отбираются по рейтингу; если OSRM недоступен, время считается по
прямой.

### SearXNG и web search

В compose есть сервис `searxng` и клиент `app/clients/searxng.py`. GigaChat умеет
`complete_with_tools` со схемой `web_search` (`app/function_schema.py`). Демо:

```bash
docker compose exec api python scripts/gigachat_search_demo.py "курс USD ЦБ сегодня"
```

В сам пятистадийный пайплайн tool-loop GigaChat пока не встроен — это инфра
для следующих фич. При этом thin digests SearXNG (короткие discovery-хинты
и городской digest ≤800 символов) уже используются в стадии `places`:
`app/services/web_intel.py` + память городов в Postgres.

## Источники данных

| Источник          | Ключ  | Что даёт                                                      |
| ----------------- | ----- | ------------------------------------------------------------- |
| Open-Meteo Geocoding | нет | автокомплит + lat/lon центра города (только RU)             |
| KudaGo            | нет   | часы работы, популярность, редакторские описания, фото — 12 городов |
| OpenTripMap       | нужен | базовый слой мест для всех остальных городов                   |
| openrouteservice  | нужен | время в пути; 2000 запросов в сутки, при отказе — публичный OSRM |
| Open-Meteo Forecast | нет | прогноз на день маршрута, 16 дней вперёд                       |
| GigaChat          | нужен | нормализация города и отбор мест; опционально tools + SearXNG  |
| SearXNG           | нет   | thin digests (хинты/дайджест) в stage `places` + demo tool-calling |

KudaGo покрывает msk, spb, nnv, kzn, ekb, nsk, smr, krd, sochi, ufa,
krasnoyarsk, vbg. Там, где он есть, места берутся оттуда: приходят настоящие
`timetable` и `favorites_count`, поэтому `ratingSource` у таких мест — `catalog`,
а не `estimate`. Отели — отдельная категория каталога и просто не запрашиваются.

Лицензия KudaGo требует индексируемую ссылку на первоисточник, поэтому каждое
место несёт `sourceUrl` / `sourceName`, и карточка её показывает.

Цен не публикует ни один бесплатный источник, поэтому стоимость остаётся нашей
оценкой и помечена `priceEstimated: true` — фронт рисует рядом хинт «Оценка».
Бесплатный вход в парк оценкой не считается. Бюджет `0` — режим «только
бесплатные места», а не «бюджет не задан».

Погода приходит только на дни внутри 16-дневного горизонта. Дальше `weather`
отсутствует, и день честно пишет, что прогноза пока нет.

Выключить обогащение, если источник лёг посреди демо:
`KUDAGO_ENABLED=false`, `WEATHER_ENABLED=false`, пустой `ORS_API_KEY`.

## Кеш в Redis

| Ключ                        | TTL    |
| --------------------------- | ------ |
| `otm:geoname:*`             | 90 дн  |
| `otm:xid:*`                 | 30 дн  |
| `osrm:*`                    | 30 дн  |
| `otm:radius:*`              | 7 дн   |
| `geo:city:*` / `geo:coords:*` | как geoname |
| `searxng:*`                 | 1 ч    |
| `gigachat:completion:*`     | 1 дн   |
| `trip:plan:*`               | 6 ч    |
| `gigachat:token`            | до истечения токена |

Плюс счётчик `otm:quota:YYYY-MM-DD` против дневного лимита OpenTripMap.

Повторный запрос с тем же черновиком отдаётся из `trip:plan:*` мгновенно. Если
нужно пересобрать маршрут заново:

```bash
docker compose exec redis redis-cli --scan --pattern 'trip:plan:*' | \
  xargs -r docker compose exec -T redis redis-cli DEL
```

## Авторизация

Фронт шлёт `Authorization: tma <initData>`.

- `AUTH_MODE=dev` (по умолчанию) — подпись не проверяется, все запросы идут от
  `DEV_USER_ID`. Так мини-приложение работает в обычном браузере.
- `AUTH_MODE=max` — проверка HMAC-подписи `initData` по схеме Telegram, которую
  MAX повторяет. Перед продом стоит сверить алгоритм с документацией MAX.

## MAX-бот

Код в `app/bot/`: клиент `platform-api2.max.ru` (заголовок `Authorization` +
сертификаты Минцифры), handlers (`/start`, `/help`, `/about` + кнопка
`open_app`), webhook и long polling. Поднимается из lifespan FastAPI.

| Переменная | Смысл |
| ---------- | ----- |
| `MAX_BOT_ENABLED` | `true` / `false` |
| `MAX_BOT_TOKEN` | токен из кабинета MAX |
| `MAX_BOT_MODE` | `auto` \| `webhook` \| `polling` \| `off` |
| `MAX_BOT_WEBHOOK_URL` | публичный `https://…/api/v1/bot/webhook` |
| `MAX_BOT_WEBHOOK_SECRET` | опционально, заголовок `X-Max-Bot-Api-Secret` |
| `MAX_WEBAPP_URL` | SPA URL (диагностика / about); в клавиатуре не кнопка |

`open_app` — **единственный** способ открыть мини-приложение из бота.
Кнопка уходит с `web_app=<username>` и `contact_id=<bot user_id>` из `GET /me`;
сам URL SPA привязывают в кабинете MAX (Расширенные настройки → ссылка).
Ссылки «Открыть в браузере» / deeplink в клавиатуре не дублируют открытие.

Если от организаторов есть **только токен** бота:
1. `MAX_BOT_TOKEN=…`, `MAX_BOT_ENABLED=true`, `MAX_BOT_MODE=polling`
2. Перезапуск API — бот начнёт long polling (webhook не нужен)
3. В чате `/start` → нативная кнопка `open_app`
4. Чтобы `open_app` открыл именно `https://2-rist.ru`, в кабинете MAX у
   этого бота должна быть прописана ссылка мини-приложения.

Прод-стенд: `MAX_WEBAPP_URL=https://2-rist.ru`, webhook (когда есть HTTPS):
`MAX_BOT_WEBHOOK_URL=https://api.2-rist.ru/api/v1/bot/webhook`,
`MAX_BOT_MODE=auto` или `webhook`.

`auto`: если задан `MAX_BOT_WEBHOOK_URL` — регистрирует webhook, иначе long
polling (удобно локально без туннеля). Из корня репо: `./trip bot on`.

Эндпоинты: `GET /api/v1/bot/status`, `POST /api/v1/bot/invite`
(в production — только с `X-Max-Bot-Api-Secret` = `MAX_BOT_WEBHOOK_SECRET`),
`POST /api/v1/bot/webhook`.

Проверка:

```bash
# в backend/.env: MAX_BOT_ENABLED=true, MAX_BOT_MODE=polling
docker compose up -d api
curl -s http://localhost:8000/api/v1/bot/status | jq .
cd backend && .venv/bin/python scripts/bot_smoke.py
# опционально отправить себе клавиатуру:
# .venv/bin/python scripts/bot_smoke.py --invite-user <ваш_max_user_id>
```

В чате с ботом: `/start` → «Открыть планировщик» (внутри MAX) или deeplink
`https://max.ru/<bot_username>?startapp`.

## GigaChat и TLS

GigaChat отдаёт сертификат, подписанный «Russian Trusted Root CA», которого нет в
обычном хранилище доверия. Сертификаты лежат в `backend/certs/` и ставятся в
образ, поэтому `GIGACHAT_VERIFY_SSL=true` работает из коробки. Флаг `false`
оставлен как аварийный переключатель.

Переменные SearXNG: `SEARXNG_URL`, `SEARXNG_ENABLED` — настройки **backend**
(`.env.example`). `SEARXNG_SECRET` и `SEARXNG_PUBLISH_PORT` относятся к
контейнеру `searxng` и передаются через `docker-compose.yml`, backend'у они не
нужны.
