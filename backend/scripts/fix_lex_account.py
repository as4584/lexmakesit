"""
One-time script: patches Lex's existing account so it works with the new email auth system.

Run on the server:
    cd /opt/ai-receptionist/backend
    doppler run -- python scripts/fix_lex_account.py

What it does:
  1. Finds the user account (by username or existing email)
  2. Sets email = thegamermasterninja@gmail.com
  3. Sets email_verified = True (bypasses verification since this is the owner's own account)
  4. Leaves the password_hash untouched if it exists
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ai_receptionist.models.user import User
from ai_receptionist.models.base import Base

TARGET_EMAIL = "thegamermasterninja@gmail.com"
# Try common usernames; script will search all if needed
KNOWN_USERNAMES = ["lex", "lexsantiago", "thegamermasterninja", "admin"]

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Run with: doppler run -- python scripts/fix_lex_account.py")
        sys.exit(1)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # First: check if email already exists
        existing = db.query(User).filter(User.email == TARGET_EMAIL).first()
        if existing:
            print(f"Account already has email {TARGET_EMAIL} (id={existing.id}, username={existing.username})")
            if not existing.email_verified:
                existing.email_verified = True
                db.commit()
                print("  → Set email_verified = True")
            else:
                print("  → email_verified already True. Nothing to do.")
            return

        # Try known usernames
        user = None
        for uname in KNOWN_USERNAMES:
            user = db.query(User).filter(User.username == uname).first()
            if user:
                print(f"Found user by username '{uname}' (id={user.id})")
                break

        if not user:
            # Show all users so Lex can identify their account
            all_users = db.query(User).all()
            print(f"Could not find user by known usernames. All users in DB ({len(all_users)}):")
            for u in all_users:
                print(f"  id={u.id}  username={u.username}  email={u.email}  verified={u.email_verified}")
            print("\nEdit KNOWN_USERNAMES in this script to match your username, then re-run.")
            sys.exit(1)

        user.email = TARGET_EMAIL
        user.email_verified = True
        user.email_verification_token = None
        user.password_reset_token = None
        db.commit()

        print(f"Done. User id={user.id} username={user.username}")
        print(f"  email           → {TARGET_EMAIL}")
        print(f"  email_verified  → True")
        print(f"\nYou can now log in at dashboard.lexmakesit.com with:")
        print(f"  Email:    {TARGET_EMAIL}")
        print(f"  Password: (your existing password)")

    finally:
        db.close()


if __name__ == "__main__":
    main()
