# Dotori Backend (Django + DRF + Channels + Celery)

## Quick Start
```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py createsuperuser
```

### Endpoints
- POST `/api/auth/register/`
- POST `/api/auth/token/`
- GET  `/api/auth/me/`
- Documents: `/api/documents/`
- Summaries:
  - POST `/api/summaries/create/`  body: `{ "source_text": "..." }`
  - GET  `/api/summaries/`
  - GET  `/api/summaries/{id}/`
- WebSocket: `ws://localhost:8000/ws/quiz/{room}/`
