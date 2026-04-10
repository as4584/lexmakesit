"""Re-set pro plan in feature flags."""
import json
import urllib.request
import jwt

ADMIN_KEY = "lRlnb_WAE9tRx3MfeMS_5qG4raT4QOamnxa-BNvEaMLPxmmjsPFgcYfO00ZyY4jg"
API = "http://localhost:8002"
token = jwt.encode({"scope": "admin"}, ADMIN_KEY, algorithm="HS256")

# Set plan
url = f"{API}/admin/tenants/innovation/plan"
data = json.dumps({"plan": "pro"}).encode()
req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}, method="PUT")
resp = urllib.request.urlopen(req)
print(f"Set plan: {resp.read().decode()}")

# Verify immediately
url2 = f"{API}/admin/tenants/innovation/flags"
req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {token}"})
resp2 = urllib.request.urlopen(req2)
print(f"Flags: {resp2.read().decode()}")
