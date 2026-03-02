"""Patch settings.py to add elevenlabs_api_key field."""
filepath = "/app/ai_receptionist/config/settings.py"
with open(filepath) as f:
    content = f.read()

if "elevenlabs_api_key" not in content:
    # Insert after openai_api_key line
    content = content.replace(
        "openai_api_key: Optional[str] = None",
        "openai_api_key: Optional[str] = None\n\n    # ElevenLabs Configuration\n    elevenlabs_api_key: Optional[str] = None",
    )
    with open(filepath, "w") as f:
        f.write(content)
    print("✅ settings.py patched with elevenlabs_api_key")
else:
    print("⏭  elevenlabs_api_key already exists in settings.py")
