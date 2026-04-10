from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable, Literal, Optional

from fastapi import Request

# ---------------------------------------------------------------------------
# Context variables – carried through the async call chain
# ---------------------------------------------------------------------------
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="-")

# Auth event context – auth.py writes here; middleware flushes on response
_auth_event_var: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "_auth_event", default=None
)

AuthEventType = Literal[
    "login_success",
    "login_failure",
    "login_locked",
    "logout",
    "token_revoked",
    "dependency_degraded",
    "dependency_recovered",
    "signup_success",
    "readiness_failed",
]


def emit_auth_event(
    event_type: AuthEventType,
    *,
    email: Optional[str] = None,
    user_id: Optional[int] = None,
    dependency: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Record a typed auth event to be flushed with the current request log line."""
    _auth_event_var.set(
        {
            "event_type": event_type,
            "email": email,
            "user_id": user_id,
            "dependency": dependency,
            "detail": detail,
        }
    )


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class _ContextFilter(logging.Filter):
    """Inject request_id and tenant_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        record.tenant_id = tenant_id_var.get()    # type: ignore[attr-defined]
        return True


class _StructuredFormatter(logging.Formatter):
    """Emit log records as single-line JSON for Loki/Promtail ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "tenant_id": getattr(record, "tenant_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_auth_event_logger = logging.getLogger("auth.events")


def configure_logging(structured: bool = False) -> None:
    """Attach context filter and optional structured formatter to the root logger."""
    root = logging.getLogger()
    if not any(isinstance(f, _ContextFilter) for f in root.filters):
        root.addFilter(_ContextFilter())
    if not root.handlers:
        handler = logging.StreamHandler()
        if structured:
            handler.setFormatter(_StructuredFormatter())
        else:
            fmt = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
            handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(handler)
    root.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Request / response middleware
# ---------------------------------------------------------------------------

async def request_context_middleware(request: Request, call_next: Callable):
    """Attach request_id + tenant_id to context; log structured access events."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    tid = (
        request.headers.get("X-Tenant-ID")
        or request.query_params.get("tenant_id")
        or "-"
    )

    request_id_var.set(rid)
    tenant_id_var.set(tid)
    _auth_event_var.set(None)

    request.state.request_id = rid
    request.state.tenant_id = tid

    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    response.headers["X-Request-ID"] = rid

    # Emit a structured access log line; include auth event if one was set
    auth_event = _auth_event_var.get()
    log_payload: dict[str, Any] = {
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": latency_ms,
        "request_id": rid,
        "tenant_id": tid,
    }
    if auth_event:
        log_payload["auth_event"] = auth_event
        # Emit dedicated auth-event log so Loki can alert on it
        level = (
            logging.WARNING
            if auth_event["event_type"] in (
                "login_failure", "login_locked", "dependency_degraded", "readiness_failed"
            )
            else logging.INFO
        )
        _auth_event_logger.log(level, json.dumps(auth_event, default=str))

    logging.getLogger("access").info(json.dumps(log_payload, default=str))
    return response
