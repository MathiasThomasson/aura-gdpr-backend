from fastapi import FastAPI
from app.api.routes import auth, users, documents, tenants, processing_activities, tasks, audit_logs
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI()

    origins = [o.strip() for o in (settings.CORS_ORIGINS or "*").split(",")] if settings.CORS_ORIGINS else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(documents.router)
    app.include_router(tenants.router)
    app.include_router(processing_activities.router)
    app.include_router(tasks.router)
    app.include_router(audit_logs.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/info")
    def info():
        return {"app": "aura-gdpr-backend"}

    return app


app = create_app()
