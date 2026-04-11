import logging
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
import aiohttp
from ai_receptionist.config.settings import get_settings
from ai_receptionist.core.di import get_tenant_mapping

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

# OpenAI Realtime API Configuration
OPENAI_MODEL = "gpt-4o-realtime-preview"
_DEFAULT_VOICE = "shimmer"

# TODO (Phase 2 – ElevenLabs TTS integration):
# When ready to stream ElevenLabs voices in live calls:
# 1. Load tenant's voice settings from DB (elevenlabs_voice_id, tts_provider)
# 2. If tts_provider == 'elevenlabs', use ElevenLabs WebSocket TTS
#    instead of OpenAI Realtime's built-in TTS.
# 3. Pipe ElevenLabs audio into Twilio via the same media stream.
# 4. Keep OpenAI Realtime for STT + LLM, but disable its TTS output.
# See: ai_receptionist/services/elevenlabs/voice_service.py

# Optimized system instructions for faster connection
SYSTEM_INSTRUCTIONS = """You are Aria, the AI Receptionist built by LexMakesIt. You are currently the LIVE DEMO at a career fair, showcasing what LexMakesIt can do for businesses.

YOUR PERSONALITY:
- Warm, confident, professional, and slightly enthusiastic
- You speak naturally like a real receptionist — not robotic
- You're proud of what LexMakesIt has built

ABOUT LEXMAKESIT:
LexMakesIt is a tech company that builds AI-powered solutions for businesses. Our flagship product is the AI Receptionist — an intelligent phone agent that answers calls 24/7, handles scheduling, takes messages, answers customer questions, and never misses a call.

KEY SELLING POINTS (weave these in naturally when relevant):
- Never miss a call again — AI answers 24/7, even nights, weekends, and holidays
- Handles appointment booking, FAQs, call routing, and message taking
- Sounds natural and professional — callers often don't realize it's AI
- Saves businesses thousands per month vs hiring a full-time receptionist
- Works for any industry: law firms, medical offices, salons, restaurants, contractors, real estate, and more
- Easy setup — we can have your AI receptionist live in under 24 hours
- Bilingual support (English and Spanish)
- Custom voice cloning — your receptionist can sound exactly how you want
- Integrates with Google Calendar, CRMs, and more
- Built by Alexander Santiago and the LexMakesIt team right here

CAREER FAIR CONTEXT:
You're demonstrating LexMakesIt's capabilities live. Be impressive. If someone calls:
1. Greet them warmly and introduce yourself as Aria, LexMakesIt's AI Receptionist
2. Ask how you can help or if they'd like to learn about what LexMakesIt does
3. If they ask about LexMakesIt, pitch our AI receptionist service enthusiastically
4. If they want to schedule a demo or meeting, take their name and number
5. If they ask about pricing, say plans start affordable and we customize to their needs — suggest they talk to Alexander for specifics
6. If they ask to speak to someone, let them know Alexander Santiago is at the booth and you can take a message

RULES:
- Always start in English. Switch languages only if the caller requests.
- Keep responses conversational (1-3 sentences) — don't monologue.
- Be honest that you're AI if asked — that's the whole point of the demo!
- Each call is independent. Start fresh every time.
- Sound excited about the tech — you ARE the product."""

LOG_EVENT_TYPES = [
    "response.content.done",
    "rate_limits.updated",
    "response.done",
    "input_audio_buffer.committed",
    "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started",
    "session.created",
    "response.cancelled",
]


@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    to: Optional[str] = Query(default=None, description="Dialed phone number (E.164)"),
):
    await websocket.accept()
    logger.info(f"Twilio WebSocket connected (to={to})")

    settings = get_settings()
    api_key = settings.openai_api_key

    # --- Per-tenant voice resolution ---
    voice = _DEFAULT_VOICE
    tts_provider = "openai"
    elevenlabs_voice_id: Optional[str] = None

    if to:
        try:
            phone_map = get_tenant_mapping()
            tenant_id = phone_map.get(to)
            if tenant_id:
                from ai_receptionist.core.database import get_db_session
                from ai_receptionist.models.tenant import Tenant

                with get_db_session() as db:
                    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
                    if tenant:
                        tts_provider = tenant.tts_provider or "openai"
                        voice = tenant.openai_voice or _DEFAULT_VOICE
                        elevenlabs_voice_id = (
                            tenant.custom_clone_voice_id or tenant.elevenlabs_voice_id
                        )
                        logger.info(
                            f"Resolved tenant {tenant_id}: tts_provider={tts_provider}, voice={voice}"
                        )
            else:
                logger.warning(f"No tenant found for To number {to}; using defaults")
        except Exception as exc:
            logger.warning(f"Tenant lookup failed ({exc}); using defaults")

    logger.info(f"Connecting to OpenAI Realtime API. Key present: {bool(api_key)}")

    if not api_key:
        logger.critical("OpenAI API Key is missing! Cannot connect to Realtime API.")
        await websocket.close(code=1008)
        return

    # Use aiohttp for OpenAI connection
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
        logger.info(f"OpenAI WSS URL: {url}")

        try:
            async with session.ws_connect(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=None, connect=15),
                max_msg_size=10_000_000,
            ) as openai_ws:
                logger.info(f"Connected to OpenAI Realtime API ({OPENAI_MODEL})")

                # Phase 1.2: Force Audio Output First
                # Enable server-side VAD for automatic turn detection.
                # When ElevenLabs is the TTS provider, disable OpenAI audio
                # output entirely — text output only, synthesis handled below.
                use_elevenlabs = tts_provider == "elevenlabs" and bool(elevenlabs_voice_id)
                session_update = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"] if use_elevenlabs else ["audio", "text"],
                        "instructions": SYSTEM_INSTRUCTIONS,
                        "input_audio_format": "g711_ulaw",
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 200,
                            "silence_duration_ms": 400,
                        },
                        "temperature": 0.7,
                    },
                }
                if not use_elevenlabs:
                    session_update["session"]["voice"] = voice
                    session_update["session"]["output_audio_format"] = "g711_ulaw"
                logger.info(f"Sending session.update (tts_provider={tts_provider})...")
                await openai_ws.send_json(session_update)

                # Lazy-load ElevenLabs service when needed
                el_service = None
                if use_elevenlabs:
                    try:
                        from ai_receptionist.services.elevenlabs.voice_service import (
                            ElevenLabsVoiceService,
                        )

                        el_service = ElevenLabsVoiceService()
                    except Exception as exc:
                        logger.warning(
                            f"ElevenLabs service init failed ({exc}); falling back to OpenAI TTS"
                        )
                        use_elevenlabs = False
                        # Re-issue session.update to re-enable OpenAI audio
                        session_update["session"]["modalities"] = ["audio", "text"]
                        session_update["session"]["voice"] = voice
                        session_update["session"]["output_audio_format"] = "g711_ulaw"
                        await openai_ws.send_json(session_update)

                stream_sid = None
                greeting_sent = False

                async def receive_from_twilio():
                    nonlocal stream_sid, greeting_sent
                    try:
                        async for message in websocket.iter_text():
                            data = json.loads(message)
                            event_type = data.get("event")

                            if event_type == "media":
                                # Forward audio to OpenAI
                                # Only forward if we have established connection?
                                # Realtime API accepts buffer append anytime.
                                audio_payload = data["media"]["payload"]
                                await openai_ws.send_json(
                                    {"type": "input_audio_buffer.append", "audio": audio_payload}
                                )
                            elif event_type == "start":
                                stream_sid = data["start"]["streamSid"]
                                logger.info(f"Stream started: {stream_sid}")

                                # NOW send the greeting after we have stream_sid
                                if not greeting_sent:
                                    logger.info(
                                        "Triggering initial greeting (after stream start)..."
                                    )
                                    greeting_modalities = (
                                        ["text"] if use_elevenlabs else ["audio", "text"]
                                    )
                                    await openai_ws.send_json(
                                        {
                                            "type": "response.create",
                                            "response": {
                                                "modalities": greeting_modalities,
                                                "instructions": "Say: Hey there! I'm Aria, the AI Receptionist built by LexMakesIt. Welcome to the career fair! How can I help you today?",
                                            },
                                        }
                                    )
                                    greeting_sent = True
                            elif event_type == "stop":
                                logger.info("Stream stopped from Twilio side")
                                await openai_ws.close()
                                break
                    except WebSocketDisconnect:
                        logger.info("Twilio WebSocket disconnected")
                    except Exception as e:
                        logger.error(f"Error in Twilio receive loop: {e}")

                async def receive_from_openai():
                    nonlocal stream_sid
                    import base64

                    accumulated_text: list[str] = []
                    try:
                        async for msg in openai_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                response = json.loads(msg.data)
                                event_type = response.get("type")

                                if not use_elevenlabs and event_type == "response.audio.delta":
                                    # Forward OpenAI audio directly to Twilio
                                    audio_delta = response.get("delta")
                                    if audio_delta and stream_sid:
                                        await websocket.send_json(
                                            {
                                                "event": "media",
                                                "streamSid": stream_sid,
                                                "media": {"payload": audio_delta},
                                            }
                                        )

                                elif use_elevenlabs and event_type == "response.text.delta":
                                    # Accumulate text for ElevenLabs synthesis
                                    delta = response.get("delta", "")
                                    if delta:
                                        accumulated_text.append(delta)

                                elif use_elevenlabs and event_type == "response.text.done":
                                    # Full turn text ready — synthesize with ElevenLabs
                                    full_text = "".join(accumulated_text).strip()
                                    accumulated_text.clear()
                                    if full_text and stream_sid and el_service:
                                        try:
                                            audio_bytes = await el_service.synthesize_for_call(
                                                elevenlabs_voice_id, full_text
                                            )
                                            # Encode and send as Twilio media frame(s)
                                            payload = base64.b64encode(audio_bytes).decode("ascii")
                                            await websocket.send_json(
                                                {
                                                    "event": "media",
                                                    "streamSid": stream_sid,
                                                    "media": {"payload": payload},
                                                }
                                            )
                                            logger.debug(
                                                f"ElevenLabs: sent {len(audio_bytes)} bytes for text={full_text[:40]!r}"
                                            )
                                        except Exception as exc:
                                            logger.error(
                                                f"ElevenLabs synthesis failed ({exc}); turn dropped"
                                            )

                                elif event_type == "input_audio_buffer.speech_started":
                                    # INTERRUPTION HANDLING: User started speaking
                                    # Cancel any ongoing AI response immediately
                                    logger.info("User interrupted - cancelling AI response")
                                    await openai_ws.send_json({"type": "response.cancel"})
                                    # Clear Twilio's audio buffer to stop playback
                                    if stream_sid:
                                        await websocket.send_json(
                                            {"event": "clear", "streamSid": stream_sid}
                                        )

                                elif event_type == "response.cancelled":
                                    logger.info("AI response cancelled due to interruption")

                                elif event_type == "response.audio.done":
                                    logger.debug("AI finished speaking")

                                elif event_type == "error":
                                    logger.error(f"OpenAI Error: {response}")

                                elif event_type in LOG_EVENT_TYPES:
                                    logger.debug(f"OpenAI Event: {event_type}")

                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error("OpenAI WebSocket connection closed with error")
                                break
                    except Exception as e:
                        logger.error(f"Error in OpenAI receive loop: {e}")

                # Run both loops concurrently; return_exceptions prevents one
                # task failure from silently killing the other.
                results = await asyncio.gather(
                    receive_from_twilio(),
                    receive_from_openai(),
                    return_exceptions=True,
                )
                for exc in results:
                    if isinstance(exc, Exception):
                        logger.error(f"Realtime bridge task raised: {exc}")

        except Exception as e:
            logger.error(f"Failed to connect to OpenAI or runtime error: {e}")
            # Try to inform Twilio?
            # Usually if WS closes, Twilio call ends or proceeds to next TwiML
            await websocket.close()
