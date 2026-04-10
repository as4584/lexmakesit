import json
import http.cookiejar
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8002"
EMAIL = "damien@innovation.com"
PASSWORD = "password123"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def call_with_cookie(path: str):
    try:
        resp = opener.open(f"{BASE}{path}")
        body = resp.read().decode("utf-8", errors="replace")
        print(f"{path} COOKIE_CODE={resp.getcode()}")
        print(body[:300])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"{path} COOKIE_CODE={exc.code}")
        print(body[:300])


def call_with_bearer(path: str, token: str):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        resp = urllib.request.urlopen(req)
        body = resp.read().decode("utf-8", errors="replace")
        print(f"{path} BEARER_CODE={resp.getcode()}")
        print(body[:300])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"{path} BEARER_CODE={exc.code}")
        print(body[:300])


payload = json.dumps({"email": EMAIL, "password": PASSWORD}).encode("utf-8")
login_req = urllib.request.Request(
    f"{BASE}/api/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
)

try:
    login_resp = opener.open(login_req)
    login_body = login_resp.read().decode("utf-8", errors="replace")
    print(f"/api/auth/login CODE={login_resp.getcode()}")
    print(login_body[:300])
    token = json.loads(login_body).get("access_token", "")
    print(f"TOKEN_PRESENT={1 if token else 0}")
except urllib.error.HTTPError as exc:
    login_body = exc.read().decode("utf-8", errors="replace")
    print(f"/api/auth/login CODE={exc.code}")
    print(login_body[:300])
    token = ""

call_with_cookie("/api/voice/current")
call_with_cookie("/api/voice/browse")
if token:
    call_with_bearer("/api/voice/current", token)
    call_with_bearer("/api/voice/browse", token)
