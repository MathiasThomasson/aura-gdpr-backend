from dotenv import load_dotenv
# Load .env before importing settings
load_dotenv()

from fastapi import FastAPI, Request
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler as fastapi_request_validation_handler
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, users, documents, tenants, processing_activities, tasks, audit_logs, ai, rag, gdpr
from app.api.v1.endpoints import (
    dashboard,
    dpia,
    tasks as tasks_placeholder,
    projects,
    documents as documents_placeholder,
    risk,
    data_subject_requests,
)
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

    app.include_router(dashboard.router)
    app.include_router(dpia.router)
    app.include_router(tasks_placeholder.router)
    app.include_router(projects.router)
    app.include_router(documents_placeholder.router)
    app.include_router(risk.router)
    app.include_router(data_subject_requests.router)

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(documents.router)
    app.include_router(tenants.router)
    app.include_router(processing_activities.router)
    app.include_router(tasks.router)
    app.include_router(audit_logs.router)
    app.include_router(ai.router)
    app.include_router(rag.router)
    app.include_router(gdpr.router)

    # Custom validation handler: for the AI analyze endpoint, return 400 instead of 422 when text exceeds max length
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        if request.url.path == "/api/ai/gdpr/analyze":
            # return 400 so frontends get a client error code for oversized text
            return JSONResponse(status_code=400, content={"detail": [str(e) for e in exc.errors()]})
        return await fastapi_request_validation_handler(request, exc)

    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/info")
    def info():
        return {"app": "aura-gdpr-backend"}

    return app


app = create_app()
