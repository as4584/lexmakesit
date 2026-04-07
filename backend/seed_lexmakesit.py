"""Seed LexMakesIt career fair demo account.

Creates:
- User: thegamermasterninja@gmail.com / Alexander Santiago
- Business: LexMakesIt (pro, active)
- Tenant: lexmakesit (pro plan)
- Phone number: +12298215986 linked to tenant
"""

import bcrypt
import sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os


def _require_row(row, context: str):
    if row is None:
        raise RuntimeError(f"Missing database row: {context}")
    return row


EMAIL = "thegamermasterninja@gmail.com"
PASSWORD = "Alexander Santiago"
FULL_NAME = "Alexander Santiago"
BUSINESS_NAME = "LexMakesIt"
TENANT_ID = "lexmakesit"
PHONE_NUMBER = "+12298215986"

# Hash password
pw_hash = bcrypt.hashpw(PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(f'Generated hash: {pw_hash[:10]}...')

# Connect to DB
db_url = os.environ.get(
    'DATABASE_URL',
    'postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist'
)
engine = create_engine(db_url)

with Session(engine) as db:
    # ── 1. Create or update user ──
    existing = db.execute(text("SELECT id FROM users WHERE email = :email"), {'email': EMAIL}).fetchone()
    if existing:
        uid = existing[0]
        print(f'User {EMAIL} already exists with id={uid} — updating password')
        db.execute(text(
            "UPDATE users SET password_hash = :pw, full_name = :name, is_active = true, is_verified = true WHERE email = :email"
        ), {'pw': pw_hash, 'name': FULL_NAME, 'email': EMAIL})
        db.commit()
    else:
        db.execute(text(
            "INSERT INTO users (email, username, password_hash, full_name, is_active, is_verified, created_at, updated_at)"
            " VALUES (:email, :email, :pw, :name, true, true, NOW(), NOW())"
        ), {'email': EMAIL, 'pw': pw_hash, 'name': FULL_NAME})
        db.commit()
        row = _require_row(
            db.execute(text("SELECT id FROM users WHERE email = :email"), {'email': EMAIL}).fetchone(),
            "created user"
        )
        uid = row[0]
        print(f'Created user {EMAIL} with id={uid}')

    # ── 2. Create or update business ──
    existing_biz = db.execute(
        text("SELECT id FROM businesses WHERE owner_email = :email"), {'email': EMAIL}
    ).fetchone()
    if existing_biz:
        biz_id = existing_biz[0]
        print(f'Business already exists with id={biz_id} — updating')
        db.execute(text(
            "UPDATE businesses SET name = :name, subscription_status = 'pro', "
            "phone_number = :phone, phone_number_status = 'active', "
            "receptionist_enabled = true, is_active = 1 "
            "WHERE id = :biz_id"
        ), {'name': BUSINESS_NAME, 'phone': PHONE_NUMBER, 'biz_id': biz_id})
        db.commit()
    else:
        db.execute(text(
            "INSERT INTO businesses (name, owner_email, subscription_status, phone_number, "
            "phone_number_status, receptionist_enabled, is_active, created_at, updated_at)"
            " VALUES (:name, :email, 'pro', :phone, 'active', true, 1, NOW(), NOW())"
        ), {'name': BUSINESS_NAME, 'email': EMAIL, 'phone': PHONE_NUMBER})
        db.commit()
        biz = _require_row(
            db.execute(text("SELECT id FROM businesses WHERE owner_email = :email"), {'email': EMAIL}).fetchone(),
            "created business"
        )
        biz_id = biz[0]
        print(f'Created business {BUSINESS_NAME} with id={biz_id}')

    # ── 3. Create tenant ──
    existing_tenant = db.execute(
        text("SELECT id FROM tenants WHERE id = :tid"), {'tid': TENANT_ID}
    ).fetchone()
    if existing_tenant:
        print(f'Tenant {TENANT_ID} already exists — updating plan to pro')
        db.execute(text(
            "UPDATE tenants SET plan = 'pro', name = :name, owner_user_id = :uid WHERE id = :tid"
        ), {'name': BUSINESS_NAME, 'uid': uid, 'tid': TENANT_ID})
        db.commit()
    else:
        db.execute(text(
            "INSERT INTO tenants (id, name, owner_user_id, plan, tts_provider, created_at, updated_at)"
            " VALUES (:tid, :name, :uid, 'pro', 'openai', NOW(), NOW())"
        ), {'tid': TENANT_ID, 'name': BUSINESS_NAME, 'uid': uid})
        db.commit()
        print(f'Created tenant {TENANT_ID}')

    # ── 4. Link phone number to tenant ──
    existing_phone = db.execute(
        text("SELECT id FROM phone_numbers WHERE phone_number = :phone"), {'phone': PHONE_NUMBER}
    ).fetchone()
    if existing_phone:
        print(f'Phone {PHONE_NUMBER} already exists — updating tenant')
        db.execute(text(
            "UPDATE phone_numbers SET tenant_id = :tid, is_active = true WHERE phone_number = :phone"
        ), {'tid': TENANT_ID, 'phone': PHONE_NUMBER})
        db.commit()
    else:
        # Use a placeholder SID if we don't have the real one yet
        twilio_sid = os.environ.get('TWILIO_PHONE_SID', 'pending_career_fair')
        db.execute(text(
            "INSERT INTO phone_numbers (tenant_id, phone_number, twilio_sid, friendly_name, is_active, created_at)"
            " VALUES (:tid, :phone, :sid, :fname, true, NOW())"
        ), {'tid': TENANT_ID, 'phone': PHONE_NUMBER, 'sid': twilio_sid, 'fname': 'LexMakesIt Career Fair'})
        db.commit()
        print(f'Linked phone {PHONE_NUMBER} to tenant {TENANT_ID}')

    # ── Verify everything ──
    u = _require_row(
        db.execute(text(
            "SELECT id, email, full_name, is_active, is_verified FROM users WHERE email = :email"
        ), {'email': EMAIL}).fetchone(),
        "verification user"
    )
    b = _require_row(
        db.execute(text(
            "SELECT id, name, subscription_status, phone_number FROM businesses WHERE owner_email = :email"
        ), {'email': EMAIL}).fetchone(),
        "verification business"
    )
    t = _require_row(
        db.execute(text(
            "SELECT id, plan FROM tenants WHERE id = :tid"
        ), {'tid': TENANT_ID}).fetchone(),
        "verification tenant"
    )
    p = _require_row(
        db.execute(text(
            "SELECT phone_number, tenant_id, is_active FROM phone_numbers WHERE phone_number = :phone"
        ), {'phone': PHONE_NUMBER}).fetchone(),
        "verification phone"
    )

    print(f'\n=== VERIFICATION ===')
    print(f'User:     id={u[0]}, email={u[1]}, name={u[2]}, active={u[3]}, verified={u[4]}')
    print(f'Business: id={b[0]}, name={b[1]}, status={b[2]}, phone={b[3]}')
    print(f'Tenant:   id={t[0]}, plan={t[1]}')
    print(f'Phone:    number={p[0]}, tenant={p[1]}, active={p[2]}')
    print(f'\nSUCCESS: LexMakesIt career fair demo is ready!')
    print(f'Login:    {EMAIL} / {PASSWORD}')
    print(f'Phone:    {PHONE_NUMBER}')
