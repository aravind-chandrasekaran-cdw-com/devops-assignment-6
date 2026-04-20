import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.logging_config import configure_logging


configure_logging()
service_name = os.getenv("SERVICE_NAME", "sample-fastapi-app")
service_version = os.getenv("SERVICE_VERSION", "1.0.0")
environment = os.getenv("ENVIRONMENT", "local")
logger = logging.getLogger(service_name)


def log_context(**extra_fields):
    return {
        "service_name": service_name,
        "service_version": service_version,
        "environment": environment,
        **extra_fields,
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_startup", extra=log_context())
    yield
    logger.info("application_shutdown", extra=log_context())


app = FastAPI(
    title="Sample FastAPI App",
    description="A minimal FastAPI service with JSON logging and Prometheus metrics.",
    lifespan=lifespan,
    version=service_version,
)

Instrumentator(excluded_handlers=["/health"]).instrument(app).expose(app, include_in_schema=False)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "request_failed",
            extra=log_context(
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                duration_ms=duration_ms,
            ),
        )
        raise

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra=log_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
        ),
    )
    return response


@app.get("/")
async def read_root():
    logger.info("root_endpoint_called", extra=log_context())
    return {
        "message": "Hello from FastAPI",
        "service_name": service_name,
        "service_version": service_version,
        "environment": environment,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service_name": service_name,
    }


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    logger.info("item_endpoint_called", extra=log_context(item_id=item_id))
    return {
        "item_id": item_id,
        "name": f"item-{item_id}",
        "service_name": service_name,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled_exception",
        extra=log_context(
            path=request.url.path,
            method=request.method,
        ),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )