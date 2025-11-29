# AURA-GDPR Backend (FastAPI)

## Overview
- FastAPI (async) on Python 3.12
- Async SQLAlchemy 2.x + asyncpg against PostgreSQL 16
- Alembic for migrations (sync engine)
- JWT auth with access + refresh tokens
- Systemd for deployment on VPS
- Absolutely no `create_all()`; all schema managed via Alembic

## Installation
1) Clone the repo and create a virtualenv (Python 3.12).
2) Install dependencies:
```
pip install -r requirements.txt
```
3) Create your `.env` from the template:
```
cp .env.example .env
```
4) Fill in values in `.env` (see Environment Variables below).

## Database setup
Follow `docs/setup-db.md` to provision PostgreSQL. Summary (run as postgres):
- Create DB `aura` and role `user` with a password.
- Grant privileges as shown in the doc.

## Running migrations
All tables come from Alembic migrations (no `create_all()`):
```
alembic upgrade head
```

## Running the app (dev)
```
uvicorn main:app --reload
```

## Deployment with systemd (VPS)
- Deploy by `git pull` on the VPS.
- Ensure `.env` is updated with the correct DATABASE_URL and SECRET_KEY.
- Apply migrations: `alembic upgrade head`
- Restart service: `systemctl restart aura-gdpr-backend`
- Check status/logs: `systemctl status aura-gdpr-backend`, `journalctl -u aura-gdpr-backend -n 100`

## Troubleshooting DB connection errors
- Verify `DATABASE_URL` in `.env` uses `postgresql+asyncpg://user:PASSWORD@localhost/aura`
- Ensure the role/password from `docs/setup-db.md` are correct.
- Confirm PostgreSQL is running and listening on localhost:5432.
- Check Alembic config uses the same URL (it is sourced from `.env` via pydantic settings).

## Environment Variables
Required (see `.env.example`):
- `DATABASE_URL`: async URL, e.g. `postgresql+asyncpg://user:CHANGEME_PASSWORD@localhost/aura`
- `SECRET_KEY`: JWT signing key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: access token lifetime in minutes
- `REFRESH_TOKEN_EXPIRE_DAYS`: refresh token lifetime in days
- `ENV`: environment name (default `production`)
- `CORS_ORIGINS`: comma-separated origins or `*`
- AI-related knobs (OLLAMA_BASE_URL, AI_MODEL, rate limits, circuit breaker, audit flags)

## Auth endpoints (already implemented)
- `/api/auth/register`
- `/api/auth/login`
- `/api/auth/refresh`
Passwords are hashed with bcrypt; JWT includes `sub`, `tenant_id`, and `role`.

## Notes
- Multi-tenant design: tenant_id is required on tenant-bound models.
- Alembic uses a sync engine; runtime uses async engine.
- The repository is the single source of truth; the VPS must not be hand-edited.
