"""Test Damien's login on production."""
import urllib.request
import urllib.error
import json

url = "http://localhost:8002/api/auth/login"
payload = json.dumps({"email": "damien@innovation.com", "password": "password123"}).encode()
req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

try:
    resp = urllib.request.urlopen(req)
    print(f"STATUS: {resp.status}")
    body = resp.read().decode()
    print(f"BODY: {body}")
    cookie = resp.getheader("Set-Cookie")
    if cookie:
        print(f"COOKIE: {cookie}")
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}: {e.read().decode()}")
