<!-- Copilot instructions for contributors and AI agents -->
# Copilot / AI Agent Instructions

This project is a small FastAPI backend using async SQLAlchemy and JWT-based auth. The goal of this file is to give an AI coding agent the concrete, discoverable context required to be productive here.

**Quick Architecture:**
- **Entry:** `main.py` — mounts routers and CORS middleware.
- **API routes:** `app/api/routes/*.py` — each file registers an `APIRouter` with a `prefix` (e.g. `/api/auth`, `/api/users`). See `auth.py` for auth flows.
- **DB layer:** `app/db/database.py` — uses `sqlalchemy.ext.asyncio.create_async_engine` + `AsyncSession` and exposes `get_db()` as a dependency.
- **Models:** SQLAlchemy models under `app/db/models/` and Pydantic schemas under `app/models/` (e.g. `User` vs `UserCreate`).
- **Auth & Security:** `app/core/security.py` (password hashing, JWT creation) and `app/core/auth.py` (token decode + `get_current_user` dependency). Token URL: `/api/auth/login`.

**Important patterns and conventions (do not change without review):**
- Async DB access: functions use `AsyncSession` and `await db.execute(...)` or `await db.get(...)`. Use `get_db()` dependency for DB access.
- Pydantic schemas named `*Create`, `*Out`; SQLAlchemy models have the same logical entities but live under `app/db/models`.
- Passwords are hashed with `passlib` (`bcrypt`). Use `hash_password()` and `verify_password()` from `app/core/security.py`.
- JWTs: `create_access_token()` encodes `{"sub": <user.id>}` and `get_current_user` expects `sub` to be present.

**Run & Dev commands (PowerShell examples):**
```powershell
# set environment variables (example)
$env:DATABASE_URL = 'postgresql+asyncpg://user:pass@localhost:5432/dbname';
$env:SECRET_KEY = 'replace-with-secure-key';

# install
pip install -r requirements.txt

# run dev server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Database & migrations:**
- `alembic.ini` and `alembic/` are present. Use `alembic upgrade head` to apply migrations. The project uses async SQLAlchemy; confirm Alembic's env.py supports async engines before generating migrations.

**Files to look at for examples:**
- `main.py` — router registration and CORS setup.
- `app/api/routes/auth.py` — register/login flows, uses `UserCreate` pydantic model and `app.db.models.user.User`.
- `app/core/security.py` — `hash_password`, `verify_password`, `create_access_token`.
- `app/core/auth.py` — `oauth2_scheme` and `get_current_user` dependency.
- `app/db/database.py` — shows `create_async_engine`, `async_session`, `Base`, and `get_db()`.

**Typical change templates (examples):**
- Add endpoint that needs DB: import `AsyncSession` and `Depends`, add `db: AsyncSession = Depends(get_db)` parameter, and use `await db.execute(...)` or `db.add(...)` + `await db.commit()` + `await db.refresh(obj)`.
- Add a new model: create SQLAlchemy model in `app/db/models/`, add matching Pydantic schema in `app/models/`, and use in route handlers.

**What to avoid / watch out for:**
- Do not convert DB code to sync without migrating all call sites — the project expects `AsyncSession` everywhere.
- Secrets & credentials: repository uses `.env` via `python-dotenv`; do not hardcode real secrets in code.
- Token format: `sub` claim is integer id stored as string in token encode; `get_current_user` converts it via `int()`.

If something is unclear or you need more examples (tests, CI, or expected error handling), ask for clarification before making broad changes.

---
Please review and tell me if you'd like more examples (e.g. a sample endpoint change or an Alembic migration example).
