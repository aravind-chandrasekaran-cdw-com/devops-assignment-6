import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import logging_loki
except ImportError:  # pragma: no cover - optional dependency for remote logging
    logging_loki = None


SERVICE_NAME = os.getenv("SERVICE_NAME", "sample-fastapi-app")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
LOKI_URL = os.getenv("LOKI_URL", "http://loki-gateway.loki.svc.cluster.local/loki/api/v1/push")
LOKI_USERNAME = os.getenv("LOKI_USERNAME")
LOKI_PASSWORD = os.getenv("LOKI_PASSWORD")


class _DynamicServiceLokiHandler(logging_loki.LokiHandler):
    def emit(self, record: logging.LogRecord) -> None:
        original_tags = dict(getattr(self, "tags", {}))
        service_tag = getattr(record, "service_name", None) or record.name
        self.tags["service"] = service_tag
        try:
            super().emit(record)
        finally:
            self.tags.clear()
            self.tags.update(original_tags)


def _build_loki_handler(log_level: str) -> logging.Handler | None:
    if not LOKI_URL or logging_loki is None:
        return None

    auth = None
    if LOKI_USERNAME and LOKI_PASSWORD:
        auth = (LOKI_USERNAME, LOKI_PASSWORD)

    handler = _DynamicServiceLokiHandler(
        url=LOKI_URL,
        tags={
            "service": SERVICE_NAME,
            "environment": ENVIRONMENT,
            "version": SERVICE_VERSION,
        },
        auth=auth,
        version="1",
    )
    handler.setLevel(log_level)
    return handler


def service_context(service_name: str, **extra_fields: Any) -> dict[str, Any]:
    return {
        "service_name": service_name,
        "service_version": SERVICE_VERSION,
        "environment": ENVIRONMENT,
        **extra_fields,
    }


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service_name": getattr(record, "service_name", SERVICE_NAME),
            "service_version": getattr(record, "service_version", SERVICE_VERSION),
            "environment": getattr(record, "environment", ENVIRONMENT),
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id

        path = getattr(record, "path", None)
        if path:
            payload["path"] = path

        method = getattr(record, "method", None)
        if method:
            payload["method"] = method

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            payload["status_code"] = status_code

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        item_id = getattr(record, "item_id", None)
        if item_id is not None:
            payload["item_id"] = item_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    loki_handler = _build_loki_handler(log_level)
    if loki_handler is not None:
        root_logger.addHandler(loki_handler)

    root_logger.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(log_level)