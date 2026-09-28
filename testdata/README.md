# Тестовые данные для проверки API

| Файл | Назначение |
|------|------------|
| `trip_draft_kazan.json` | Типовой черновик поездки (Казань, бюджет 8000 ₽) — тело `POST /api/v1/trips` |
| `trip_draft_free_budget.json` | Режим «только бесплатные места» (`budget: 0`) |

## Как прогнать без UI

```bash
./trip up

# создать поездку
curl -sS -X POST http://localhost:8000/api/v1/trips \
  -H 'Content-Type: application/json' \
  -d @testdata/trip_draft_kazan.json

# подставить id из ответа
curl -sS http://localhost:8000/api/v1/trips/<id>
curl -N http://localhost:8000/api/v1/trips/<id>/stream
```

При `AUTH_MODE=dev` заголовок MAX не нужен.  
Контракт проверок: [`DATA-API.yaml`](../DATA-API.yaml). Полная схема: [`openapi.yaml`](../openapi.yaml).
