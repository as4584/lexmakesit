from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
import asyncio
import json
import logging

from ai_receptionist.core.database import get_db, get_session_local
from ai_receptionist.core.auth import get_current_user, TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/business", tags=["business"])

# --- Schemas ---

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    timezone: Optional[str] = None
    greeting_style: Optional[str] = None
    business_hours: Optional[str] = None
    common_services: Optional[str] = None
    receptionist_enabled: Optional[bool] = None

# --- Endpoints ---

@router.get("/me")
async def get_business_me(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.email:
        raise HTTPException(status_code=401, detail="No email in token")

    row = db.execute(
        text(
            "SELECT id, name, industry, description, phone_number, timezone, "
            "business_hours, greeting_style, common_services, is_active, faqs, "
            "created_at, updated_at, subscription_status, minutes_used, "
            "minutes_limit, stripe_customer_id, receptionist_enabled, "
            "phone_number_status, balance_minutes "
            "FROM businesses WHERE owner_email = :email LIMIT 1"
        ),
        {"email": user.email}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Business not found")

    return {
        "id": str(row[0]),
        "name": row[1],
        "industry": row[2],
        "description": row[3],
        "phone_number": row[4],
        "timezone": row[5],
        "business_hours": row[6],
        "greeting_style": row[7],
        "common_services": row[8],
        "is_active": row[9],
        "faqs": row[10],
        "created_at": str(row[11]) if row[11] else None,
        "updated_at": str(row[12]) if row[12] else None,
        "subscription_status": row[13],
        "minutes_used": row[14],
        "minutes_limit": row[15],
        "stripe_customer_id": row[16],
        "receptionist_enabled": row[17],
        "phone_number_status": row[18],
        "balance_minutes": row[19],
    }


@router.put("/me")
async def update_business_me(
    update_data: BusinessUpdate,
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.email:
        raise HTTPException(status_code=401, detail="No email in token")

    row = db.execute(
        text("SELECT id FROM businesses WHERE owner_email = :email LIMIT 1"),
        {"email": user.email}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Business not found")

    updates = {k: v for k, v in update_data.model_dump().items() if v is not None}

    if updates:
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["biz_id"] = row[0]
        db.execute(
            text(f"UPDATE businesses SET {set_clause}, updated_at = now() WHERE id = :biz_id"),
            updates
        )
        db.commit()

    return await get_business_me(user=user, db=db)


@router.get("/calls")
async def get_call_history(
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.email:
        raise HTTPException(status_code=401, detail="No email in token")

    biz = db.execute(
        text("SELECT id FROM businesses WHERE owner_email = :email LIMIT 1"),
        {"email": user.email}
    ).fetchone()

    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    calls = db.execute(
        text(
            "SELECT id, call_sid, from_number, duration, intent, status, created_at "
            "FROM calls WHERE business_id = :bid "
            "ORDER BY created_at DESC LIMIT 50"
        ),
        {"bid": biz[0]}
    ).fetchall()

    return [
        {
            "id": c[0],
            "call_sid": c[1],
            "from_number": c[2],
            "duration": c[3],
            "intent": c[4],
            "status": c[5],
            "created_at": str(c[6]) if c[6] else None,
        }
        for c in calls
    ]


@router.get("/events/calls")
async def stream_calls(user: TokenData = Depends(get_current_user)):
    """SSE endpoint — polls DB every 3s and pushes new calls to connected clients."""
    if not user.email:
        raise HTTPException(status_code=401, detail="No email in token")

    email = user.email

    async def event_generator():
        db = get_session_local()()
        try:
            biz = db.execute(
                text("SELECT id FROM businesses WHERE owner_email = :email LIMIT 1"),
                {"email": email}
            ).fetchone()

            if not biz:
                yield f'data: {json.dumps({"type": "error", "message": "business not found"})}\n\n'
                return

            business_id = biz[0]

            last_row = db.execute(
                text("SELECT COALESCE(MAX(id), 0) FROM calls WHERE business_id = :bid"),
                {"bid": business_id}
            ).fetchone()
            last_id = last_row[0]

            yield f'data: {json.dumps({"type": "connected"})}\n\n'

            while True:
                await asyncio.sleep(3)
                db.expire_all()
                try:
                    new_calls = db.execute(
                        text(
                            "SELECT id, call_sid, from_number, duration, intent, status, created_at "
                            "FROM calls WHERE business_id = :bid AND id > :lid ORDER BY id ASC"
                        ),
                        {"bid": business_id, "lid": last_id}
                    ).fetchall()

                    for c in new_calls:
                        event = {
                            "type": "new_call",
                            "id": c[0],
                            "call_sid": c[1],
                            "from_number": c[2],
                            "duration": c[3],
                            "intent": c[4],
                            "status": c[5],
                            "created_at": str(c[6]) if c[6] else None,
                        }
                        yield f"data: {json.dumps(event)}\n\n"
                        last_id = max(last_id, c[0])

                    # keepalive to prevent proxy timeouts
                    yield ": keepalive\n\n"

                except Exception as e:
                    logger.error(f"[SSE] poll error: {e}")
                    yield f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n'
                    break
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
