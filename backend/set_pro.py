"""Set Damien's Innovation business to pro plan (DB + in-memory flags)."""
import json
import urllib.request
import urllib.error
import jwt  # PyJWT

from sqlalchemy import create_engine, text

DB_URL = "postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist"
ADMIN_KEY = "lRlnb_WAE9tRx3MfeMS_5qG4raT4QOamnxa-BNvEaMLPxmmjsPFgcYfO00ZyY4jg"
API_BASE = "http://localhost:8002"

# 1. Update DB — set subscription_status to 'pro'
print("1. Updating subscription_status to 'pro' in database...")
engine = create_engine(DB_URL)
with engine.begin() as conn:
    conn.execute(text("UPDATE businesses SET subscription_status = 'pro' WHERE id = 11"))
    biz = conn.execute(text(
        "SELECT id, name, subscription_status, phone_number FROM businesses WHERE id = 11"
    )).mappings().first()
    if biz is None:
        raise RuntimeError("Business id=11 not found")
    print(f"   {dict(biz)}")

# 2. Set in-memory plan via admin API
print("\n2. Setting in-memory feature flag plan to 'pro'...")
token = jwt.encode({"scope": "admin"}, ADMIN_KEY, algorithm="HS256")

# Use "innovation" as tenant_id (the business name slug)
url = f"{API_BASE}/admin/tenants/innovation/plan"
data = json.dumps({"plan": "pro"}).encode()
req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}, method="PUT")

try:
    resp = urllib.request.urlopen(req)
    print(f"   STATUS: {resp.status}")
    print(f"   BODY: {resp.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"   ERROR {e.code}: {e.read().decode()}")

# 3. Verify flags
print("\n3. Verifying feature flags...")
url2 = f"{API_BASE}/admin/tenants/innovation/flags"
req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {token}"})
try:
    resp2 = urllib.request.urlopen(req2)
    print(f"   Flags: {resp2.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"   ERROR {e.code}: {e.read().decode()}")

print("\nDONE: Innovation is now on the 'pro' plan")
