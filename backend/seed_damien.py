import bcrypt
import sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os


def _require_row(row: object, context: str) -> tuple[object, ...]:
    if row is None:
        raise RuntimeError(f"Missing database row: {context}")
    return row  # type: ignore[return-value]

# Hash password
pw_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
print('Generated hash: ' + pw_hash[:10] + '...')

# Connect to DB
db_url = os.environ.get('DATABASE_URL', 'postgresql://ai_receptionist_user:secure_pg_password_2024@postgres:5432/ai_receptionist')
engine = create_engine(db_url)

with Session(engine) as db:
    # Check if user already exists
    existing = db.execute(text("SELECT id FROM users WHERE email = 'innovation'")).fetchone()
    if existing:
        print('User innovation already exists with id=' + str(existing[0]))
    else:
        db.execute(text(
            "INSERT INTO users (email, password_hash, full_name, is_active, is_verified, created_at)"
            " VALUES (:email, :pw, :name, true, true, NOW())"
        ), {'email': 'innovation', 'pw': pw_hash, 'name': 'Damien 1st client'})
        db.commit()
        row = _require_row(
            db.execute(text("SELECT id FROM users WHERE email = 'innovation'")).fetchone(),
            "created user",
        )
        print('Created user innovation with id=' + str(row[0]))

    # Create business for Damien
    user_row = _require_row(
        db.execute(text("SELECT id FROM users WHERE email = 'innovation'")).fetchone(),
        "user lookup",
    )
    uid = user_row[0]

    existing_biz = db.execute(text("SELECT id FROM businesses WHERE owner_email = 'innovation'")).fetchone()
    if existing_biz:
        print('Business already exists with id=' + str(existing_biz[0]))
    else:
        db.execute(text(
            "INSERT INTO businesses (name, owner_email, subscription_status, created_at, updated_at)"
            " VALUES (:name, :email, 'active', NOW(), NOW())"
        ), {'name': 'Innovation', 'email': 'innovation'})
        db.commit()
        biz = _require_row(
            db.execute(text("SELECT id FROM businesses WHERE owner_email = 'innovation'")).fetchone(),
            "created business",
        )
        print('Created business Innovation with id=' + str(biz[0]))

    # Verify
    u = _require_row(
        db.execute(text("SELECT id, email, full_name, is_active, is_verified FROM users WHERE email = 'innovation'")).fetchone(),
        "verification user",
    )
    b = _require_row(
        db.execute(text("SELECT id, name, subscription_status FROM businesses WHERE owner_email = 'innovation'")).fetchone(),
        "verification business",
    )
    print('User: id=' + str(u[0]) + ', email=' + str(u[1]) + ', name=' + str(u[2]) + ', active=' + str(u[3]) + ', verified=' + str(u[4]))
    print('Business: id=' + str(b[0]) + ', name=' + str(b[1]) + ', status=' + str(b[2]))
    print('SUCCESS: Damien is ready to login!')
