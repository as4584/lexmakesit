"""
Voice Settings API endpoints (PRODUCTION version).

Provides voice browsing, selection, and cloning for business accounts.
All endpoints require an authenticated user (cookie or Bearer JWT).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import io

from ai_receptionist.core.database import get_db
from ai_receptionist.core.auth import get_current_user, TokenData
from ai_receptionist.models.business import Business
from ai_receptionist.services.elevenlabs.voice_service import (
    ElevenLabsVoiceService,
    get_elevenlabs_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Max upload size: 10 MB
MAX_AUDIO_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/ogg",
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

def _get_business(db: Session, user: TokenData) -> Business:
    """Look up the business for the authenticated user."""
    # Try business_id from token first
    if user.business_id:
        biz = db.query(Business).filter(Business.id == int(user.business_id)).first()
        if biz:
            return biz
    # Fall back to email lookup
    if user.email:
        biz = db.query(Business).filter(Business.owner_email == user.email).first()
        if biz:
            return biz
    raise HTTPException(status_code=404, detail="business not found for user")


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
    biz = _get_business(db, user)
    return VoiceSettingsOut(
        tts_provider=getattr(biz, 'tts_provider', None) or "openai",
        elevenlabs_voice_id=getattr(biz, 'elevenlabs_voice_id', None),
        elevenlabs_voice_name=getattr(biz, 'elevenlabs_voice_name', None),
        elevenlabs_voice_preview_url=getattr(biz, 'elevenlabs_voice_preview_url', None),
        custom_clone_voice_id=getattr(biz, 'custom_clone_voice_id', None),
        custom_clone_voice_name=getattr(biz, 'custom_clone_voice_name', None),
        has_clone=getattr(biz, 'custom_clone_voice_id', None) is not None,
    )


@router.put("/select")
def select_voice(
    body: VoiceSelectRequest,
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a voice selection (from library or from clone).

    Saves the voice ID and name to the business record.
    """
    biz = _get_business(db, user)

    biz.elevenlabs_voice_id = body.voice_id
    biz.elevenlabs_voice_name = body.voice_name
    biz.elevenlabs_voice_preview_url = body.preview_url
    # Future: uncomment when ready to switch live calls
    # biz.tts_provider = "elevenlabs"
    db.commit()

    logger.info(f"Business {biz.id} selected voice: {body.voice_name} ({body.voice_id})")
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
):
    """Upload an audio clip to create an instant voice clone.

    Limit: **1 clone per account**.  Delete the existing clone first
    if you want to create a new one.
    """
    biz = _get_business(db, user)

    # Enforce 1-clone-per-account
    if getattr(biz, 'custom_clone_voice_id', None):
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
        raise HTTPException(status_code=422, detail="Audio file is too small — needs at least 30 seconds")

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
    biz.custom_clone_voice_id = voice.voice_id
    biz.custom_clone_voice_name = voice.name
    db.commit()

    logger.info(f"Business {biz.id} cloned voice: {voice.voice_id} ({voice.name})")
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
):
    """Delete the user's cloned voice (allows re-cloning)."""
    biz = _get_business(db, user)

    if not getattr(biz, 'custom_clone_voice_id', None):
        raise HTTPException(status_code=404, detail="No cloned voice to delete")

    old_id = biz.custom_clone_voice_id

    # Delete from ElevenLabs
    try:
        await el.delete_voice(old_id)
    except Exception as e:
        logger.warning(f"Failed to delete voice {old_id} from ElevenLabs: {e}")

    # If the selected voice was the clone, clear it
    if biz.elevenlabs_voice_id == old_id:
        biz.elevenlabs_voice_id = None
        biz.elevenlabs_voice_name = None
        biz.elevenlabs_voice_preview_url = None

    biz.custom_clone_voice_id = None
    biz.custom_clone_voice_name = None
    db.commit()

    logger.info(f"Business {biz.id} deleted clone: {old_id}")
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
    biz = _get_business(db, user)

    if not getattr(biz, 'custom_clone_voice_id', None):
        raise HTTPException(status_code=404, detail="No cloned voice found")

    try:
        audio = await el.generate_preview(biz.custom_clone_voice_id)
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
