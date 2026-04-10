"""Patch di.py to load tenant mapping from the businesses table."""
import re

# Read the current di.py
with open("/app/ai_receptionist/core/di.py", "r") as f:
    content = f.read()

# Replace the get_tenant_mapping function with a DB-backed version
old_func = '''def get_tenant_mapping() -> Dict[str, str]:
    """Provide a phone-number-to-tenant_id mapping.

    In production, this could come from a database or settings. Overridden in tests.
    """
    return {}'''

new_func = '''def get_tenant_mapping() -> Dict[str, str]:
    """Provide a phone-number-to-tenant_id mapping.

    Loads from the businesses table so new numbers are picked up automatically.
    Falls back to empty dict on error.
    """
    try:
        from ai_receptionist.core.database import SessionLocal
        from ai_receptionist.models.business import Business
        db = SessionLocal()
        try:
            businesses = db.query(Business).filter(
                Business.phone_number.isnot(None),
                Business.is_active == True,
            ).all()
            mapping = {}
            for biz in businesses:
                # Use business name lowercased as tenant_id
                tenant_id = biz.name.lower().replace(" ", "-") if biz.name else str(biz.id)
                mapping[biz.phone_number] = tenant_id
            return mapping
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to load tenant mapping from DB, using empty")
        return {}'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open("/app/ai_receptionist/core/di.py", "w") as f:
        f.write(content)
    print("SUCCESS: Patched di.py with DB-backed tenant mapping")
else:
    # Try a more flexible match
    pattern = r'def get_tenant_mapping\(\).*?return \{\}'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_func.replace('\\', '\\\\'), content, flags=re.DOTALL)
        with open("/app/ai_receptionist/core/di.py", "w") as f:
            f.write(content)
        print("SUCCESS: Patched di.py (regex match)")
    else:
        print("WARNING: Could not find get_tenant_mapping to patch")
        print("Current content around get_tenant_mapping:")
        idx = content.find("get_tenant_mapping")
        if idx >= 0:
            print(content[max(0,idx-50):idx+200])
