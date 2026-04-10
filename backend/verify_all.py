"""Final verification: all Damien/Innovation provisioning."""
import json
import urllib.request
import urllib.error
from sqlalchemy import create_engine, text

DB_URL = "postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist"
API = "http://localhost:8002"

engine = create_engine(DB_URL)
print("=" * 60)
print("DAMIEN / INNOVATION - FINAL VERIFICATION")
print("=" * 60)

# 1. User record
print("\n1. USER RECORD:")
with engine.connect() as c:
    u = c.execute(text("SELECT id, email, full_name, is_active, is_verified FROM users WHERE id=10")).mappings().first()
    if u is None:
        raise RuntimeError("User id=10 not found")
    for k, v in dict(u).items():
        print(f"   {k}: {v}")

# 2. Business record
print("\n2. BUSINESS RECORD:")
with engine.connect() as c:
    b = c.execute(text("SELECT id, name, phone_number, phone_number_sid, phone_number_status, subscription_status, is_active, receptionist_enabled, owner_email FROM businesses WHERE id=11")).mappings().first()
    if b is None:
        raise RuntimeError("Business id=11 not found")
    for k, v in dict(b).items():
        print(f"   {k}: {v}")

# 3. Login test
print("\n3. LOGIN TEST:")
payload = json.dumps({"email": "damien@innovation.com", "password": "password123"}).encode()
req = urllib.request.Request(f"{API}/api/auth/login", data=payload, headers={"Content-Type": "application/json"}, method="POST")
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print(f"   Status: {resp.status} OK")
    print(f"   Token: {data['access_token'][:30]}...")
    print(f"   User: {data['user']['full_name']} ({data['user']['email']})")
    print(f"   Business ID: {data['user']['business_id']}")
    cookie = resp.getheader("Set-Cookie")
    if cookie:
        print(f"   Cookie: {cookie[:60]}...")
except urllib.error.HTTPError as e:
    print(f"   FAILED: {e.code} - {e.read().decode()}")

# 4. Tenant mapping
print("\n4. TENANT MAPPING:")
try:
    from ai_receptionist.core.di import get_tenant_mapping
    mapping = get_tenant_mapping()
    print(f"   Mapping: {mapping}")
except Exception as e:
    print(f"   Could not test mapping: {e}")

# 5. Feature flags
print("\n5. FEATURE FLAGS:")
import jwt as pyjwt
ADMIN_KEY = "lRlnb_WAE9tRx3MfeMS_5qG4raT4QOamnxa-BNvEaMLPxmmjsPFgcYfO00ZyY4jg"
token = pyjwt.encode({"scope": "admin"}, ADMIN_KEY, algorithm="HS256")
req2 = urllib.request.Request(f"{API}/admin/tenants/innovation/flags", headers={"Authorization": f"Bearer {token}"})
try:
    resp2 = urllib.request.urlopen(req2)
    flags = json.loads(resp2.read().decode())
    print(f"   {flags}")
except urllib.error.HTTPError as e:
    print(f"   FAILED: {e.code} - {e.read().decode()}")

print("\n" + "=" * 60)
print("ALL CHECKS COMPLETE")
print("=" * 60)
