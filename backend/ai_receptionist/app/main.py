from fastapi import FastAPI, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import os
import time

from ai_receptionist.config.settings import Settings, get_settings
from ai_receptionist.app.api.twilio import router as twilio_router
from ai_receptionist.app.api.admin import router as admin_router
from ai_receptionist.app.api.oauth import router as oauth_router
from ai_receptionist.app.api.auth import router as auth_router
from ai_receptionist.app.api.voice_settings import router as voice_settings_router
# from ai_receptionist.api.twilio_voice import router as twilio_voice_router # Removed
from ai_receptionist.api.realtime import router as realtime_router
from ai_receptionist.services.voice.endpoints import router as voice_router
from ai_receptionist.app.middleware import configure_logging, request_context_middleware, emit_auth_event
from ai_receptionist.utils.encryption import LEGACY_ENCRYPTION_SALT_B64
from ai_receptionist.core.database import check_db_health

logger = logging.getLogger(__name__)


app = FastAPI(title="AI Receptionist", version="0.1.0")

settings = get_settings()

# CORS — must be registered before any router
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Tenant-ID"],
)
if settings.encryption_salt == LEGACY_ENCRYPTION_SALT_B64:
    logger.critical(
        "Default legacy encryption salt detected. Rotate ENCRYPTION_SALT and run token migration."
    )

# Startup time for uptime reporting
_start_time = time.time()

# Startup validation — fail loudly if JWT key is absent at boot
if not (os.getenv("JWT_SECRET_KEY") or settings.jwt_secret_key or
        os.getenv("ADMIN_PRIVATE_KEY") or settings.admin_private_key):
    logger.critical(
        "JWT signing key not configured. Set JWT_SECRET_KEY before starting. "
        "Auth endpoints will fail at runtime."
    )

# Get static directory path
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health(settings: Settings = Depends(get_settings)):
    """Liveness probe — returns 200 as long as the process is running."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/readiness")
def readiness():
    """
    Readiness probe — checks that critical dependencies are reachable.
    Returns 200 with per-dependency status, or 503 if any required dep is down.
    """
    checks: dict[str, str] = {}
    all_ready = True

    # Database check
    db_ok, db_detail = check_db_health()
    checks["database"] = "ok" if db_ok else f"degraded: {db_detail}"
    if not db_ok:
        all_ready = False
        emit_auth_event("readiness_failed", dependency="database", detail=db_detail)

    # Redis check (optional dependency — degraded is warned, not fatal)
    try:
        import importlib
        redis_module = importlib.import_module("redis")
        _settings = get_settings()
        rc = redis_module.Redis.from_url(
            _settings.get_redis_url(),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        rc.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"degraded: {exc}"
        emit_auth_event("dependency_degraded", dependency="redis", detail=str(exc))

    status_code = 200 if all_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_ready,
            "uptime_seconds": round(time.time() - _start_time, 1),
            "checks": checks,
        },
    )


# Serve the ChatGPT-style UI at root
@app.get("/")
def root():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return JSONResponse({"name": "ai-receptionist", "version": "0.1.0"})

# Debug routes
@app.post("/test-ping")
def test_ping():
    return {"msg": "pong"}

@app.post("/twilio/test-voice")
def test_voice(CallSid: str = Form(...)):
    return {"sid": CallSid}

# Mount routers
# Prioritize voice_router to ensure /twilio/voice is registered correctly
app.include_router(voice_router, prefix="/twilio")
app.include_router(twilio_router, prefix="/twilio")
app.include_router(realtime_router, prefix="/twilio")
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(voice_settings_router)
app.include_router(oauth_router)

# Observability: attach request id and tenant id to context and logs
configure_logging(structured=settings.structured_logging)
app.middleware("http")(request_context_middleware)
