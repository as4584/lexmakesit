from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from ai_receptionist.config.settings import Settings, get_settings
from ai_receptionist.app.api.twilio import router as twilio_router
from ai_receptionist.app.api.admin import router as admin_router
from ai_receptionist.api.twilio_voice import router as twilio_voice_router
from ai_receptionist.services.voice.endpoints import router as voice_router
from ai_receptionist.app.middleware import configure_logging, request_context_middleware

logger = logging.getLogger(__name__)


app = FastAPI(title="AI Receptionist", version="0.1.0")

# Get static directory path
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "env": settings.app_env}


# Serve the ChatGPT-style UI at root
@app.get("/")
def root():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return JSONResponse({"name": "ai-receptionist", "version": "0.1.0"})

# Mount routers
app.include_router(twilio_router, prefix="/twilio")
app.include_router(admin_router)
app.include_router(twilio_voice_router)
app.include_router(voice_router)

# Observability: attach request id and tenant id to context and logs
configure_logging()
app.middleware("http")(request_context_middleware)
