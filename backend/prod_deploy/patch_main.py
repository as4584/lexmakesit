"""Patch main.py to add voice settings router."""
import re

filepath = "/app/ai_receptionist/app/main.py"
with open(filepath) as f:
    content = f.read()

# Add import
import_line = "from ai_receptionist.app.api.voice_settings import router as voice_settings_router"
if import_line not in content:
    # Insert after the auth import
    content = content.replace(
        "from ai_receptionist.core.auth import get_current_user, TokenData",
        "from ai_receptionist.core.auth import get_current_user, TokenData\n" + import_line,
    )

# Add router registration
router_line = "app.include_router(voice_settings_router)"
if router_line not in content:
    content = content.replace(
        "app.include_router(auth_router)",
        "app.include_router(auth_router)\napp.include_router(voice_settings_router)",
    )

with open(filepath, "w") as f:
    f.write(content)
print("✅ main.py patched with voice_settings_router")
