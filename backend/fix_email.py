"""Fix Damien's email to a valid format using SQLAlchemy."""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist")
old_email = "innovation"
new_email = "damien@innovation.com"

with engine.begin() as conn:
    conn.execute(text("UPDATE users SET email = :new WHERE email = :old"), {"new": new_email, "old": old_email})
    conn.execute(text("UPDATE businesses SET owner_email = :new WHERE owner_email = :old"), {"new": new_email, "old": old_email})

    row = conn.execute(text("SELECT id, email, full_name, is_active, is_verified FROM users WHERE email = :e"), {"e": new_email}).mappings().first()
    print(f"User: {dict(row)}")
    biz = conn.execute(text("SELECT id, name, owner_email, subscription_status FROM businesses WHERE owner_email = :e"), {"e": new_email}).mappings().first()
    print(f"Business: {dict(biz)}")

print(f"DONE: Email updated from '{old_email}' to '{new_email}'")
