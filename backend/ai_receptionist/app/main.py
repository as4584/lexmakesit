from fastapi import FastAPI, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import logging

from ai_receptionist.config.settings import Settings, get_settings
from ai_receptionist.app.api.twilio import router as twilio_router
from ai_receptionist.app.api.admin import router as admin_router
from ai_receptionist.app.api.oauth import router as oauth_router
from ai_receptionist.app.api.auth import router as auth_router
from ai_receptionist.app.api.voice_settings import router as voice_settings_router
# from ai_receptionist.api.twilio_voice import router as twilio_voice_router # Removed
from ai_receptionist.api.realtime import router as realtime_router
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

@app.get("/api/business/calls")
async def get_business_calls():
    """Return call history from the in-memory call monitor."""
    try:
        from call_monitor import monitor
        calls = []
        for call in monitor.call_history:
            start_time = call.get("start_time")
            calls.append({
                "from_number": call.get("from", "Unknown"),
                "status": "completed",
                "duration": round(call.get("duration", 0)),
                "created_at": start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time),
                "end_time": call.get("end_time"),
                "end_reason": call.get("end_reason", "completed"),
                "language": call.get("language", "en"),
                "transcript": [
                    {"speaker": speaker, "text": text}
                    for speaker, text in call.get("transcript", [])
                ],
            })
        return list(reversed(calls))  # newest first
    except Exception as e:
        logger.error(f"Failed to fetch calls: {e}")
        return []


@app.post("/twilio/transfer")
async def transfer_to_google_voice(request: Request, To: str = Form(None), CallSid: str = Form(None)):
    """
    Called by Twilio when it needs to transfer the caller to the owner's Google Voice number.
    Looks up the tenant by the 'To' number, then dials the Google Voice number.
    Falls back to a polite message if no Google Voice number is set.
    """
    from twilio.twiml.voice_response import VoiceResponse, Dial
    from ai_receptionist.services.voice.tenant_configs import get_tenant_config

    config = get_tenant_config(To)
    gv_number = config.get("google_voice_number")

    resp = VoiceResponse()
    if gv_number:
        resp.say("Please hold while I connect you.", voice="Polly.Joanna")
        dial = Dial(timeout=30, action="/twilio/transfer-complete")
        dial.number(gv_number)
        resp.append(dial)
    else:
        resp.say(
            "I'm sorry, I'm unable to transfer your call right now. "
            "Please try reaching us by email or call back during business hours.",
            voice="Polly.Joanna"
        )
        resp.hangup()

    return Response(content=str(resp), media_type="application/xml")


@app.post("/twilio/transfer-complete")
async def transfer_complete(DialCallStatus: str = Form(None)):
    """Called after a transfer attempt — handles no-answer gracefully."""
    from twilio.twiml.voice_response import VoiceResponse
    resp = VoiceResponse()
    if DialCallStatus in ("no-answer", "busy", "failed"):
        resp.say(
            "I wasn't able to reach anyone. Please try again later or send us an email.",
            voice="Polly.Joanna"
        )
    resp.hangup()
    return Response(content=str(resp), media_type="application/xml")


class LearnWebsiteRequest(BaseModel):
    url: str


@app.post("/api/business/learn-website")
async def learn_website(body: LearnWebsiteRequest):
    """Fetch a website's text content and ingest it into the RAG context for this tenant."""
    import urllib.request
    import re

    url = body.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AI Receptionist)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch website: {e}")

    # Strip HTML tags to get readable text
    text = re.sub(r"<style[^>]*>.*?</style>", " ", raw_html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text[:12000]  # cap at ~12k chars to stay within context limits

    if len(text) < 100:
        raise HTTPException(status_code=422, detail="Website returned too little readable content.")

    # Store as a tenant knowledge document (in-memory for now; swap for Pinecone upsert when ready)
    try:
        from ai_receptionist.services.rag import get_vector_store
        store = get_vector_store()
        # Use a stable doc ID so re-learning overwrites the old version
        await store.upsert("default", doc_id="website_content", text=text, metadata={"source": url})
        message = f"Aria has read {url} and will use it to answer caller questions."
    except Exception:
        # RAG not configured — store in-memory on the business_config module as a fallback
        import ai_receptionist.services.voice.business_config as bc
        bc.WEBSITE_CONTEXT = text
        bc.WEBSITE_URL = url
        message = f"Website content loaded into memory. Connect Pinecone to persist across restarts."

    logger.info(f"Website ingested: {url} ({len(text)} chars)")
    return {"ok": True, "chars_ingested": len(text), "message": message}


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
configure_logging()
app.middleware("http")(request_context_middleware)
