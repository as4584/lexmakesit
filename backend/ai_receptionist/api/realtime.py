import logging
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import aiohttp
from ai_receptionist.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

# OpenAI Realtime API Configuration
OPENAI_MODEL = "gpt-4o-realtime-preview"
VOICE = "shimmer"

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
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Twilio WebSocket connected")

    settings = get_settings()
    api_key = settings.openai_api_key

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
            async with session.ws_connect(url, headers=headers) as openai_ws:
                logger.info(f"Connected to OpenAI Realtime API ({OPENAI_MODEL})")

                # Phase 1.2: Force Audio Output First
                # Enable server-side VAD for automatic turn detection
                session_update = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["audio", "text"],
                        "instructions": SYSTEM_INSTRUCTIONS,
                        "voice": VOICE,
                        "input_audio_format": "g711_ulaw",
                        "output_audio_format": "g711_ulaw",
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 200,
                            "silence_duration_ms": 400,
                        },
                        "temperature": 0.7,
                    },
                }
                logger.info("Sending session.update...")
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
                                    await openai_ws.send_json(
                                        {
                                            "type": "response.create",
                                            "response": {
                                                "modalities": ["audio", "text"],
                                                "instructions": "Say: Hey there! I'm Aria, the AI Receptionist built by LexMakesIt. Welcome to the career fair! How can I help you today?",
                                            },
                                        }
                                    )
                                    greeting_sent = True
                            elif event_type == "stop":
                                logger.info("Stream stopped from Twilio side")
                                # Close OpenAI connection?
                                # await openai_ws.close()
                                break
                    except WebSocketDisconnect:
                        logger.info("Twilio WebSocket disconnected")
                    except Exception as e:
                        logger.error(f"Error in Twilio receive loop: {e}")

                async def receive_from_openai():
                    nonlocal stream_sid
                    try:
                        async for msg in openai_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                response = json.loads(msg.data)
                                event_type = response.get("type")

                                if event_type == "response.audio.delta":
                                    # Forward audio to Twilio
                                    audio_delta = response.get("delta")
                                    if audio_delta and stream_sid:
                                        await websocket.send_json(
                                            {
                                                "event": "media",
                                                "streamSid": stream_sid,
                                                "media": {"payload": audio_delta},
                                            }
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

                # Run both loops
                await asyncio.gather(receive_from_twilio(), receive_from_openai())

        except Exception as e:
            logger.error(f"Failed to connect to OpenAI or runtime error: {e}")
            # Try to inform Twilio?
            # Usually if WS closes, Twilio call ends or proceeds to next TwiML
            await websocket.close()
