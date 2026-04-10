"""Inspect Damien's business and schema."""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist")
with e.connect() as c:
    cols = c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='businesses' ORDER BY ordinal_position")).fetchall()
    print("COLUMNS:", [r[0] for r in cols])
    biz = c.execute(text("SELECT * FROM businesses WHERE id=11")).mappings().first()
    if biz:
        for k, v in dict(biz).items():
            print(f"  {k}: {v}")
    else:
        print("BIZ NOT FOUND at id=11")
    # also check user
    user = c.execute(text("SELECT * FROM users WHERE id=10")).mappings().first()
    if user:
        print("\nUSER:")
        for k, v in dict(user).items():
            print(f"  {k}: {v}")
