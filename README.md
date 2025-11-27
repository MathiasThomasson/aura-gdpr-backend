# AURA-GDPR Backend (FastAPI)

## Quick start
- Create and activate a virtualenv (Python 3.11+), then install deps:  
  `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and fill values (SECRET_KEY, DATABASE_URL, etc.).
- Run migrations: `alembic upgrade head`
- Start API (dev): `uvicorn main:app --reload`
- Run tests: `pytest`

## Configuration
- Central settings live in `app/core/config.py` (pydantic-settings).  
  `config/settings.py` is deprecated and only kept as a stub for legacy scripts.
- Use an **async** DB URL for runtime (e.g., `postgresql+asyncpg://...`); Alembic auto-normalizes to sync for migrations.
- CORS origins: comma-separated or `*`.
- AI/Ollama settings and audit/circuit-breaker controls are defined in `.env.example`.

## Development notes
- Multi-tenant by design: tenant_id is required on tenant-bound models and queries must filter by the current tenant.
- Tests auto-run migrations against a local sqlite DB (see `tests/conftest.py`).
- Auth: JWTs carry `sub`, `tenant_id`, and `role`. Refresh tokens rotate on each use and are revoked on reuse; tokens are tenant-bound.
- Roles: allowed values are `owner`, `admin`, `user`. Registering into an existing tenant requires `tenant_id`; tenant creation sets an `owner`.
- Domains: tasks, processing activities, documents, audit logs, AI, and RAG are tenant-scoped. Documents and RAG content may contain personal data—treat and delete per tenant policy.
- RAG: ingestion chunks tenant documents with checksums and embeddings; searches are tenant-filtered. AI input/output are size-limited and hashed/truncated in audit by default.
- GDPR/DSAR: `/api/gdpr/export/*` and `/api/gdpr/delete/*` allow tenant-scoped export/anonymize flows; user emails are anonymized and related data soft-deleted or cascaded. Audit logs avoid PII.
- AI safety: auth required; configurable `AI_MAX_INPUT_CHARS`, `AI_MAX_OUTPUT_CHARS`, `AI_LOGGING_LEVEL` (none/hash/truncated/full), and `AI_DISABLE_PROMPT_STORAGE`. Circuit reset is admin-only.
