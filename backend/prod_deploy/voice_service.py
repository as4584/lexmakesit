"""
ElevenLabs Voice Service.

Handles voice browsing (library), instant voice cloning (1 per account),
and TTS preview generation.  All calls use the REST API so we keep
the dependency surface minimal (no SDK — just httpx).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class VoiceInfo:
    voice_id: str
    name: str
    category: str                # e.g. "premade", "cloned", "professional"
    description: Optional[str]
    labels: Dict[str, str]       # {"accent": "american", "gender": "female", …}
    preview_url: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "labels": self.labels,
            "preview_url": self.preview_url,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ElevenLabsVoiceService:
    """Thin wrapper around ElevenLabs REST API.

    Only touches the endpoints our API key has access to:
      - GET  /v1/voices           (Voices – Read)
      - GET  /v1/voices/{id}      (Voices – Read)
      - POST /v1/voices/add       (Voices – Write)  → instant clone
      - DELETE /v1/voices/{id}    (Voices – Write)
      - POST /v1/text-to-speech/{id}/stream  (TTS – Access)
      - GET  /v1/models           (Models – Access)
      - GET  /v1/user/subscription  (User – Read)
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        # Also try loading from settings if available
        if not self._api_key:
            try:
                from ai_receptionist.config.settings import get_settings
                self._api_key = getattr(get_settings(), 'elevenlabs_api_key', None)
            except Exception:
                pass
        if not self._api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured")

    # -- helpers --

    def _headers(self) -> Dict[str, str]:
        return {"xi-api-key": self._api_key}

    def _url(self, path: str) -> str:
        return f"{ELEVENLABS_BASE}{path}"

    # -- Voice Library --

    async def list_voices(self) -> List[VoiceInfo]:
        """Fetch all available voices (built-in + user's clones)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self._url("/voices"), headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        voices: List[VoiceInfo] = []
        for v in data.get("voices", []):
            voices.append(VoiceInfo(
                voice_id=v["voice_id"],
                name=v["name"],
                category=v.get("category", "premade"),
                description=v.get("description"),
                labels=v.get("labels") or {},
                preview_url=v.get("preview_url"),
            ))
        return voices

    async def get_voice(self, voice_id: str) -> VoiceInfo:
        """Get single voice details."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                self._url(f"/voices/{voice_id}"),
                headers=self._headers(),
            )
            resp.raise_for_status()
            v = resp.json()

        return VoiceInfo(
            voice_id=v["voice_id"],
            name=v["name"],
            category=v.get("category", "premade"),
            description=v.get("description"),
            labels=v.get("labels") or {},
            preview_url=v.get("preview_url"),
        )

    # -- Instant Voice Clone --

    async def clone_voice(self, name: str, audio_bytes: bytes, filename: str = "clip.mp3") -> VoiceInfo:
        """Create an instant voice clone from an audio file (30 s – 5 min).

        Returns:
            VoiceInfo with the newly created voice_id.
        """
        files = {"files": (filename, audio_bytes, "audio/mpeg")}
        form_data = {"name": name}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self._url("/voices/add"),
                headers=self._headers(),
                data=form_data,
                files=files,
            )
            resp.raise_for_status()
            v = resp.json()

        logger.info(f"Created ElevenLabs clone: {v['voice_id']} ({name})")
        return VoiceInfo(
            voice_id=v["voice_id"],
            name=name,
            category="cloned",
            description=f"Instant clone for {name}",
            labels={},
            preview_url=v.get("preview_url"),
        )

    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice.  Returns True on success."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                self._url(f"/voices/{voice_id}"),
                headers=self._headers(),
            )
        if resp.status_code in (200, 204):
            logger.info(f"Deleted ElevenLabs voice: {voice_id}")
            return True
        logger.warning(f"Delete voice {voice_id} returned {resp.status_code}")
        return False

    # -- TTS Preview --

    async def generate_preview(self, voice_id: str, text: str = "Hi, this is your AI receptionist. How can I help you today?") -> bytes:
        """Generate a short TTS clip (returns raw mp3 bytes).

        Uses eleven_turbo_v2 for lowest latency.  Keep *text* short
        (~20 words) to stay well within free-tier character limits.
        """
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self._url(f"/text-to-speech/{voice_id}/stream"),
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.content

    # -- Usage / Quota --

    async def get_usage(self) -> Dict[str, Any]:
        """Return character quota info from the user subscription."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                self._url("/user/subscription"),
                headers=self._headers(),
            )
            resp.raise_for_status()
            sub = resp.json()

        return {
            "character_count": sub.get("character_count", 0),
            "character_limit": sub.get("character_limit", 0),
            "voice_limit": sub.get("voice_limit", 0),
            "tier": sub.get("tier", "free"),
        }


# ---------------------------------------------------------------------------
# Singleton helper (used as FastAPI dependency)
# ---------------------------------------------------------------------------

_instance: Optional[ElevenLabsVoiceService] = None


def get_elevenlabs_service() -> ElevenLabsVoiceService:
    """FastAPI dependency returning the shared service instance."""
    global _instance
    if _instance is None:
        _instance = ElevenLabsVoiceService()
    return _instance
