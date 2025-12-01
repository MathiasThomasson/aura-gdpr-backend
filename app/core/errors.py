from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DatabaseError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException


async def handle_validation_error(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": "; ".join([err.get("msg", "Invalid input") for err in exc.errors()])})


async def handle_http_error(request: Request, exc: HTTPException | StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "An error occurred"
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


async def handle_database_error(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=500, content={"error": "Database error. Please retry later."})


async def handle_integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"error": "Request conflicts with existing data."})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(DatabaseError, handle_database_error)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
