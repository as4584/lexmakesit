import requests
s = requests.Session()
r = s.post("http://localhost:8002/api/auth/login",
           json={"email": "damien@innovation.com", "password": "password123"})
print("Login:", r.status_code)
if r.status_code == 200:
    # Test voice browse
    r2 = s.get("http://localhost:8002/api/voice/browse")
    print("Browse:", r2.status_code)
    if r2.status_code == 200:
        voices = r2.json()
        print(f"Found {len(voices)} voices")
        if voices:
            print(f"First: {voices[0]['name']} ({voices[0]['category']})")
    else:
        print("Error:", r2.text[:300])

    # Test current voice
    r3 = s.get("http://localhost:8002/api/voice/current")
    print("Current:", r3.status_code, r3.text[:200])
else:
    print("Login error:", r.text[:300])
