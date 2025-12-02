import logging
import time
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Request, HTTPException
from fastapi.exception_handlers import request_validation_exception_handler as fastapi_request_validation_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt

from app.api.routes import (
    auth,
    users,
    documents,
    tenants,
    processing_activities,
    tasks,
    audit_logs,
    ai,
    rag,
    gdpr,
    api_keys,
    system,
    onboarding,
    user_progress,
    analytics,
)
from app.api.v1.endpoints import (
    dashboard,
    dpia,
    dsr,
    public_dsr,
    incidents,
    notifications,
    ai_audit,
    ai_policies,
    ai_qa,
    billing,
    iam,
    workspace_iam,
    platform_admin,
    tasks as tasks_placeholder,
    projects,
    documents as documents_placeholder,
    policies,
    ropa,
    cookies,
    toms,
    risk,
    data_subject_requests,
)
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, request_logging_middleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import rate_limit_dependency

configure_logging()
PROCESS_START_TIME = time.time()
global_rate_limiter = rate_limit_dependency("global", limit=100, window_seconds=60)


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
    app.add_middleware(SecurityHeadersMiddleware)

    @app.middleware("http")
    async def _demo_tenant_guard(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and settings.DEMO_TENANT_ID is not None:
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1]
                try:
                    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    tenant_id = claims.get("tenant_id")
                    if tenant_id is not None and int(tenant_id) == int(settings.DEMO_TENANT_ID):
                        return JSONResponse(status_code=403, content={"detail": "Demo tenant is read-only."})
                except Exception:
                    pass
        return await call_next(request)

    @app.middleware("http")
    async def _global_rate_limit(request: Request, call_next):
        try:
            await global_rate_limiter(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": getattr(exc, "detail", "Too many requests")})
        return await call_next(request)

    app.middleware("http")(request_logging_middleware)

    app.include_router(dashboard.router)
    app.include_router(dpia.router)
    app.include_router(policies.router)
    app.include_router(ropa.router)
    app.include_router(cookies.router)
    app.include_router(toms.router)
    app.include_router(tasks_placeholder.router)
    app.include_router(projects.router)
    app.include_router(documents_placeholder.router)
    app.include_router(risk.router)
    app.include_router(data_subject_requests.router)
    app.include_router(dsr.router)
    app.include_router(public_dsr.router)
    app.include_router(incidents.router)
    app.include_router(notifications.router)
    app.include_router(ai_audit.router)
    app.include_router(ai_policies.router)
    app.include_router(ai_qa.router)
    app.include_router(billing.router)
    app.include_router(iam.router)
    app.include_router(workspace_iam.router)
    app.include_router(platform_admin.router)

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
    app.include_router(api_keys.router)
    app.include_router(system.router)
    app.include_router(system.public_router)
    app.include_router(onboarding.router)
    app.include_router(user_progress.router)
    app.include_router(analytics.router)

    # Custom validation handler: return 400 instead of 422 when text exceeds max length for AI endpoint
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        if request.url.path == "/api/ai/gdpr/analyze":
            return JSONResponse(status_code=400, content={"detail": [str(e) for e in exc.errors()]})
        return await fastapi_request_validation_handler(request, exc)

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    register_error_handlers(app)

    @app.get("/health", summary="Basic health", description="Unauthenticated liveness probe.")
    def health():
        return {"status": "ok"}

    @app.get("/info", summary="App info", description="Basic deployment metadata.")
    def info():
        return {"app": "aura-gdpr-backend"}

    app.state.process_start_time = PROCESS_START_TIME
    return app


app = create_app()
