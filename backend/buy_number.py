"""Buy a Twilio US local number and assign to Damien's business (id=11)."""
# pyright: reportMissingTypeStubs=false

import os
from twilio.rest import Client
from sqlalchemy import create_engine, text

# Twilio
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

# DB
DB_URL = "postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist"
engine = create_engine(DB_URL)

BUSINESS_ID = 11
WEBHOOK_BASE = "https://receptionist.lexmakesit.com"

print("1. Searching for available US local numbers...")
available = client.available_phone_numbers("US").local.list(
    limit=5,
    voice_enabled=True,
    sms_enabled=True,
)

if not available:
    print("ERROR: No available US local numbers found")
    exit(1)

for i, num in enumerate(available):
    print(f"  [{i}] {num.phone_number} ({num.locality}, {num.region})")

# Pick the first one
chosen = available[0]
print(f"\n2. Purchasing {chosen.phone_number}...")

purchased = client.incoming_phone_numbers.create(
    phone_number=chosen.phone_number,
    friendly_name="Innovation - Damien",
    voice_url=f"{WEBHOOK_BASE}/api/twilio/webhook",
    voice_method="POST",
    status_callback=f"{WEBHOOK_BASE}/api/twilio/status",
    status_callback_method="POST",
)

print(f"   SID: {purchased.sid}")
print(f"   Number: {purchased.phone_number}")
print(f"   Friendly name: {purchased.friendly_name}")

print(f"\n3. Updating business {BUSINESS_ID} in database...")
with engine.begin() as conn:
    conn.execute(
        text("""
            UPDATE businesses 
            SET phone_number = :phone, 
                phone_number_sid = :sid, 
                phone_number_status = 'active'
            WHERE id = :biz_id
        """),
        {"phone": purchased.phone_number, "sid": purchased.sid, "biz_id": BUSINESS_ID}
    )
    # Verify
    biz = conn.execute(
        text("SELECT id, name, phone_number, phone_number_sid, phone_number_status FROM businesses WHERE id = :id"),
        {"id": BUSINESS_ID}
    ).mappings().first()
    if biz is None:
        raise RuntimeError(f"Business {BUSINESS_ID} not found after update")
    print(f"   Business updated: {dict(biz)}")

print(f"\nSUCCESS: Purchased {purchased.phone_number} for Innovation (Damien)")
