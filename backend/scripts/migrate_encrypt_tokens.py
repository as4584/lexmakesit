"""Re-encrypt Google OAuth tokens with a rotated ENCRYPTION_SALT.

Usage examples:
  python scripts/migrate_encrypt_tokens.py --dry-run
  python scripts/migrate_encrypt_tokens.py --new-salt "$ENCRYPTION_SALT"
  python scripts/migrate_encrypt_tokens.py --old-salt "<legacy_or_old_b64>" --new-salt "<new_b64>"
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_receptionist.core.database import get_db_session
from ai_receptionist.models.oauth import GoogleOAuthToken
from ai_receptionist.utils.encryption import (
    LEGACY_ENCRYPTION_SALT_B64,
    decrypt_token_with_salt,
    encrypt_token_with_salt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rotate OAuth token encryption salt")
    parser.add_argument(
        "--old-salt",
        default=LEGACY_ENCRYPTION_SALT_B64,
        help="Base64-encoded old encryption salt (default: legacy static salt)",
    )
    parser.add_argument(
        "--new-salt",
        default=os.environ.get("ENCRYPTION_SALT", ""),
        help="Base64-encoded new encryption salt (default: ENCRYPTION_SALT env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate decrypt/re-encrypt flow without writing to DB",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    old_salt = (args.old_salt or "").strip()
    new_salt = (args.new_salt or "").strip()

    if not old_salt:
        print("ERROR: --old-salt must be set", file=sys.stderr)
        return 2
    if not new_salt:
        print("ERROR: --new-salt or ENCRYPTION_SALT must be set", file=sys.stderr)
        return 2

    if old_salt == new_salt:
        print("ERROR: old and new salts are identical; refusing no-op migration", file=sys.stderr)
        return 2

    migrated = 0
    failed = 0

    print("Starting OAuth token salt migration")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'WRITE'}")

    with get_db_session() as db:
        rows = db.query(GoogleOAuthToken).all()
        total = len(rows)
        print(f"Found {total} token record(s)")

        for row in rows:
            try:
                access_plain = decrypt_token_with_salt(
                    row.access_token_encrypted, old_salt
                )
                refresh_plain = decrypt_token_with_salt(
                    row.refresh_token_encrypted, old_salt
                )

                if not args.dry_run:
                    row.access_token_encrypted = cast(
                        Any, encrypt_token_with_salt(access_plain, new_salt)
                    )
                    row.refresh_token_encrypted = cast(
                        Any, encrypt_token_with_salt(refresh_plain, new_salt)
                    )
                    row.updated_at = cast(
                        Any, datetime.now(timezone.utc).replace(tzinfo=None)
                    )

                migrated += 1
            except Exception as exc:
                failed += 1
                print(
                    f"FAILED tenant_id={row.tenant_id} id={row.id}: {exc}",
                    file=sys.stderr,
                )

        if failed:
            print(
                f"Migration aborted: {failed} record(s) failed, {migrated} succeeded",
                file=sys.stderr,
            )
            raise RuntimeError("Token migration failed")

    print(f"Migration complete: {migrated} record(s) processed, {failed} failed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError:
        raise SystemExit(1)
