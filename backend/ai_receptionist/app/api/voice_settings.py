"""
Voice Settings API endpoints.

Provides voice browsing, selection, and cloning for tenant accounts.
All endpoints require an authenticated user (Bearer JWT).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import io

from ai_receptionist.core.database import get_db
from ai_receptionist.app.api.auth import TokenData, get_current_user
from ai_receptionist.models.tenant import Tenant
from ai_receptionist.services.elevenlabs.voice_service import (
    ElevenLabsVoiceService,
    get_elevenlabs_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Max upload size: 10 MB
MAX_AUDIO_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/webm",
}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class VoiceSelectRequest(BaseModel):
    voice_id: str
    voice_name: str
    preview_url: Optional[str] = None


class VoiceSettingsOut(BaseModel):
    tts_provider: str
    openai_voice: Optional[str] = "shimmer"
    elevenlabs_voice_id: Optional[str] = None
    elevenlabs_voice_name: Optional[str] = None
    elevenlabs_voice_preview_url: Optional[str] = None
    custom_clone_voice_id: Optional[str] = None
    custom_clone_voice_name: Optional[str] = None
    has_clone: bool = False

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tenant(db: Session, user: TokenData) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.owner_user_id == user.user_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found for user")
    return tenant


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/browse")
async def browse_voices(
    category: Optional[str] = None,
    user: TokenData = Depends(get_current_user),
    el: ElevenLabsVoiceService = Depends(get_elevenlabs_service),
):
    """Browse the ElevenLabs voice library.

    Optional query param `category` to filter (e.g. 'premade', 'professional').
    Returns list of voices with preview URLs (playable client-side, zero cost).
    """
    voices = await el.list_voices()

    if category:
        cat_lower = category.lower()
        voices = [v for v in voices if v.category.lower() == cat_lower]

    # Sort: premade first, then by name
    voices.sort(key=lambda v: (0 if v.category == "premade" else 1, v.name))

    return [v.to_dict() for v in voices]


@router.get("/browse/{voice_id}")
async def get_voice_detail(
    voice_id: str,
    user: TokenData = Depends(get_current_user),
    el: ElevenLabsVoiceService = Depends(get_elevenlabs_service),
):
    """Get details for a single voice."""
    try:
        voice = await el.get_voice(voice_id)
        return voice.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"voice not found: {e}")


@router.get("/current", response_model=VoiceSettingsOut)
def get_current_voice(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's current voice selection."""
    tenant = _get_tenant(db, user)
    return VoiceSettingsOut(
        tts_provider=tenant.tts_provider or "openai",
        openai_voice=tenant.openai_voice or "shimmer",
        elevenlabs_voice_id=tenant.elevenlabs_voice_id,
        elevenlabs_voice_name=tenant.elevenlabs_voice_name,
        elevenlabs_voice_preview_url=tenant.elevenlabs_voice_preview_url,
        custom_clone_voice_id=tenant.custom_clone_voice_id,
        custom_clone_voice_name=tenant.custom_clone_voice_name,
        has_clone=tenant.custom_clone_voice_id is not None,
    )


@router.put("/select")
def select_voice(
    body: VoiceSelectRequest,
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Confirm a voice selection (from library or from clone).

    Saves the voice ID and name to the tenant record.
    """
    tenant = _get_tenant(db, user)

    tenant.elevenlabs_voice_id = body.voice_id
    tenant.elevenlabs_voice_name = body.voice_name
    tenant.elevenlabs_voice_preview_url = body.preview_url
    tenant.tts_provider = "elevenlabs"
    db.commit()

    logger.info(f"Tenant {tenant.id} selected voice: {body.voice_name} ({body.voice_id})")
    return {
        "ok": True,
        "voice_id": body.voice_id,
        "voice_name": body.voice_name,
    }


@router.post("/clone")
async def clone_voice(
    name: str = Form(..., description="Display name for the cloned voice"),
    audio_file: UploadFile = File(..., description="Audio file (mp3/wav/m4a, 30s-5min)"),
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    el: ElevenLabsVoiceService = Depends(get_elevenlabs_service),
) -> dict[str, Any]:
    """Upload an audio clip to create an instant voice clone.

    Limit: **1 clone per account**.  Delete the existing clone first
    if you want to create a new one.
    """
    tenant = _get_tenant(db, user)

    # Enforce 1-clone-per-account
    if tenant.custom_clone_voice_id:
        raise HTTPException(
            status_code=409,
            detail="You already have a cloned voice. Delete it first to create a new one.",
        )

    # Validate content type
    ct = audio_file.content_type or ""
    if ct not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio format: {ct}. Use mp3, wav, m4a, ogg, or webm.",
        )

    # Read & validate size
    audio_bytes = await audio_file.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    if len(audio_bytes) < 1024:
        raise HTTPException(
            status_code=422, detail="Audio file is too small — needs at least 30 seconds"
        )

    # Create clone via ElevenLabs
    try:
        voice = await el.clone_voice(
            name=name,
            audio_bytes=audio_bytes,
            filename=audio_file.filename or "clip.mp3",
        )
    except Exception as e:
        logger.error(f"ElevenLabs clone failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Voice cloning failed: {e}")

    # Persist to DB
    tenant.custom_clone_voice_id = voice.voice_id
    tenant.custom_clone_voice_name = voice.name
    db.commit()

    logger.info(f"Tenant {tenant.id} cloned voice: {voice.voice_id} ({voice.name})")
    return {
        "ok": True,
        "voice_id": voice.voice_id,
        "voice_name": voice.name,
        "preview_url": voice.preview_url,
    }


@router.delete("/clone")
async def delete_clone(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    el: ElevenLabsVoiceService = Depends(get_elevenlabs_service),
) -> dict[str, Any]:
    """Delete the user's cloned voice (allows re-cloning)."""
    tenant = _get_tenant(db, user)

    if not tenant.custom_clone_voice_id:
        raise HTTPException(status_code=404, detail="No cloned voice to delete")

    old_id = tenant.custom_clone_voice_id

    # Delete from ElevenLabs
    try:
        await el.delete_voice(old_id)
    except Exception as e:
        logger.warning(f"Failed to delete voice {old_id} from ElevenLabs: {e}")

    # If the selected voice was the clone, clear it
    if tenant.elevenlabs_voice_id == old_id:
        tenant.elevenlabs_voice_id = None
        tenant.elevenlabs_voice_name = None
        tenant.elevenlabs_voice_preview_url = None

    tenant.custom_clone_voice_id = None
    tenant.custom_clone_voice_name = None
    db.commit()

    logger.info(f"Tenant {tenant.id} deleted clone: {old_id}")
    return {"ok": True, "deleted_voice_id": old_id}


@router.get("/clone/preview")
async def preview_clone(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    el: ElevenLabsVoiceService = Depends(get_elevenlabs_service),
):
    """Generate a short TTS preview of the user's cloned voice.

    Returns audio/mpeg stream.  Uses ~100 characters of TTS quota.
    """
    tenant = _get_tenant(db, user)

    if not tenant.custom_clone_voice_id:
        raise HTTPException(status_code=404, detail="No cloned voice found")

    try:
        audio = await el.generate_preview(tenant.custom_clone_voice_id)
    except Exception as e:
        logger.error(f"Preview generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Preview generation failed: {e}")

    return StreamingResponse(
        io.BytesIO(audio),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=preview.mp3"},
    )


@router.get("/usage")
async def get_usage(
    user: TokenData = Depends(get_current_user),
    el: ElevenLabsVoiceService = Depends(get_elevenlabs_service),
):
    """Return ElevenLabs character usage / quota info."""
    try:
        usage = await el.get_usage()
        return usage
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch usage: {e}")


# ---------------------------------------------------------------------------
# Google Voice / Bring Your Own Number
# ---------------------------------------------------------------------------


class GoogleVoiceRequest(BaseModel):
    google_voice_number: Optional[str] = None  # null to remove


@router.put("/google-voice")
def set_google_voice_number(
    body: GoogleVoiceRequest,
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save or remove a Google Voice number for this tenant.

    When set, callers can choose to be transferred to this number
    instead of (or after) speaking to the AI receptionist.
    """
    import re

    tenant = _get_tenant(db, user)

    number = body.google_voice_number
    if number:
        # Normalize to E.164 — strip formatting, add +1 if needed
        digits = re.sub(r"\D", "", number)
        if len(digits) == 10:
            digits = "1" + digits
        if len(digits) == 11 and digits.startswith("1"):
            number = "+" + digits
        else:
            raise HTTPException(
                status_code=422, detail="Please enter a valid US phone number (10 digits)."
            )

    tenant.google_voice_number = number
    db.commit()

    logger.info(f"Tenant {tenant.id} set google_voice_number: {number}")
    return {"ok": True, "google_voice_number": number}


@router.get("/google-voice")
def get_google_voice_number(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current Google Voice number for this tenant."""
    tenant = _get_tenant(db, user)
    return {"google_voice_number": tenant.google_voice_number}


# ---------------------------------------------------------------------------
# OpenAI Voice Selection
# ---------------------------------------------------------------------------

OPENAI_VOICES = {"alloy", "ash", "coral", "echo", "onyx", "sage", "shimmer", "verse"}


class OpenAIVoiceRequest(BaseModel):
    voice: str


@router.put("/openai-voice")
def select_openai_voice(
    body: OpenAIVoiceRequest,
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Select an OpenAI built-in voice and switch provider to 'openai'."""
    if body.voice not in OPENAI_VOICES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown OpenAI voice: {body.voice}. Choose from: {', '.join(sorted(OPENAI_VOICES))}",
        )
    tenant = _get_tenant(db, user)
    tenant.openai_voice = body.voice
    tenant.tts_provider = "openai"
    db.commit()
    logger.info(f"Tenant {tenant.id} set openai_voice: {body.voice}")
    return {"ok": True, "openai_voice": body.voice}
