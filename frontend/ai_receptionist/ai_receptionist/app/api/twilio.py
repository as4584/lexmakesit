from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, Response, status

from ai_receptionist.core.di import get_telephony_service, get_tenant_mapping
from ai_receptionist.services.telephony.telephony import TelephonyService

"""
Twilio webhook router

SOLID notes:
- Single Responsibility: this module handles HTTP concerns for Twilio webhooks only (routing, parsing request, DI).
- Open/Closed: behavior can be extended by swapping the TelephonyService via DI without modifying this router.
- Liskov Substitution: any TelephonyService implementation can be injected as long as it respects the interface.
- Interface Segregation: TelephonyService exposes only methods needed by HTTP layer (validate_signature, enqueue_call).
- Dependency Inversion: depends on TelephonyService abstraction; concrete Twilio implementation is wired in DI.

Mocking in CI:
- validate_signature should be mocked to return True/False in unit tests.
- Redis enqueue is simulated by an in-memory list via the TelephonyService test double.
"""


router = APIRouter()


@router.post("/webhook")
async def twilio_webhook(
    request: Request,
    telephony: TelephonyService = Depends(get_telephony_service),
    tenant_mapping: Dict[str, str] = Depends(get_tenant_mapping),
):
    # Read raw body for signature validation (mockable in tests)
    body_bytes = await request.body()
    if not telephony.validate_signature(request.headers, body_bytes, url=str(request.url)):
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    # Parse payload (Twilio sends application/x-www-form-urlencoded for voice calls)
    if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        form = await request.form()
        payload: Dict[str, Any] = dict(form)
    else:
        payload = await request.json()

    caller = payload.get("From") or payload.get("Caller")
    to_number = payload.get("To")
    tenant_id = tenant_mapping.get(to_number) if to_number else None
    if tenant_id is None:
        tenant_id = "default"

    event = {
        "start_ts": time.time(),
        "caller": caller,
        "tenant_id": tenant_id,
    }
    await telephony.enqueue_call(event)

    # In production, return TwiML for voice use-cases. Here we just ack.
    return Response(status_code=status.HTTP_200_OK)
