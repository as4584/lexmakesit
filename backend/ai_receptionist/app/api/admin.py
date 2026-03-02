from __future__ import annotations

import os
from typing import Dict

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException

from sqlalchemy.orm import Session

from ai_receptionist.core.database import get_db
from ai_receptionist.core.di import get_feature_flag_service
from ai_receptionist.services.flags.service import FeatureFlagService


router = APIRouter(prefix="/admin", tags=["admin"])


def _verify_admin_jwt(authorization: str | None = Header(default=None)) -> Dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    key = os.environ.get("ADMIN_PRIVATE_KEY")
    if not key:
        # Allow Settings-based keys if desired in future; env keeps it simple
        raise HTTPException(status_code=500, detail="admin key not configured")
    try:
        payload = jwt.decode(token, key, algorithms=["HS256"])
        if payload.get("scope") != "admin":
            raise HTTPException(status_code=403, detail="forbidden")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")


@router.put("/tenants/{tenant_id}/plan")
def set_plan(
    tenant_id: str,
    body: Dict[str, str],
    svc: FeatureFlagService = Depends(get_feature_flag_service),
    _: Dict = Depends(_verify_admin_jwt),
    db: Session = Depends(get_db),
):
    plan = (body or {}).get("plan")
    if not plan:
        raise HTTPException(status_code=422, detail="plan is required")
    flags = svc.set_tenant_plan(tenant_id, plan, admin_user="api")

    # Persist plan to DB (best-effort – table may not exist yet)
    try:
        from ai_receptionist.models.tenant import Tenant
        tenant = db.query(Tenant).get(tenant_id)
        if tenant:
            tenant.plan = plan
            db.commit()
    except Exception:
        pass

    return {"ok": True, "tenant": tenant_id, "plan": plan, "flags": flags}


@router.put("/tenants/{tenant_id}/flags/{flag}")
def set_flag(tenant_id: str, flag: str, body: Dict[str, bool], svc: FeatureFlagService = Depends(get_feature_flag_service), _: Dict = Depends(_verify_admin_jwt)):
    enable = bool((body or {}).get("enable"))
    flags = svc.set_tenant_flag(tenant_id, flag, enable, admin_user="api")
    return {"ok": True, "tenant": tenant_id, "flag": flag, "enable": enable, "flags": flags}


@router.get("/tenants/{tenant_id}/flags")
def show_flags(tenant_id: str, svc: FeatureFlagService = Depends(get_feature_flag_service), _: Dict = Depends(_verify_admin_jwt)):
    return svc.get_effective_flags(tenant_id)


# ---------------------------------------------------------------------------
# Phone number provisioning
# ---------------------------------------------------------------------------


@router.post("/tenants/{tenant_id}/phone-number")
def provision_phone_number(
    tenant_id: str,
    body: Dict[str, str] | None = None,
    _: Dict = Depends(_verify_admin_jwt),
    db: "Session" = Depends(get_db),
):
    """Buy a US local number from Twilio and assign it to *tenant_id*."""
    from twilio.rest import Client as TwilioClient

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise HTTPException(status_code=500, detail="Twilio credentials not configured")

    # Verify tenant exists
    from ai_receptionist.models.tenant import Tenant
    tenant = db.query(Tenant).get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"tenant '{tenant_id}' not found")

    twilio = TwilioClient(account_sid, auth_token)

    # Optional: caller can request a specific area_code
    area_code = (body or {}).get("area_code")
    search_params: Dict[str, object] = {"limit": 1}
    if area_code:
        search_params["area_code"] = area_code

    available = twilio.available_phone_numbers("US").local.list(**search_params)
    if not available:
        raise HTTPException(status_code=404, detail="no available numbers found")

    # Purchase the number
    base_url = os.environ.get("BASE_URL", "https://ai.lexmakesit.com")
    purchased = twilio.incoming_phone_numbers.create(
        phone_number=available[0].phone_number,
        voice_url=f"{base_url}/twilio/voice",
        voice_method="POST",
        friendly_name=f"{tenant.name} AI Line",
    )

    # Persist in DB
    from ai_receptionist.models.phone_number import PhoneNumber
    pn = PhoneNumber(
        tenant_id=tenant_id,
        phone_number=purchased.phone_number,
        twilio_sid=purchased.sid,
        friendly_name=purchased.friendly_name,
    )
    db.add(pn)
    db.commit()
    db.refresh(pn)

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "phone_number": pn.phone_number,
        "twilio_sid": pn.twilio_sid,
        "friendly_name": pn.friendly_name,
    }
