"""Durable storage for contact enquiries and waitlist signups.

Why this exists: /api/contact previously depended entirely on an outbound
notification (email or Discord) succeeding. Neither was configured in
production, so a submission was thanked and then discarded. Notifications
are best-effort by nature — an SMTP outage should never lose a lead — so
the message is written down first and notified second.

The connection is optional on purpose. If the database is unreachable the
application still serves every page; it simply reports that a submission
could not be stored rather than pretending it was received.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:  # psycopg is optional so the app still boots without it
    from psycopg_pool import AsyncConnectionPool
except Exception:  # pragma: no cover - exercised only when the driver is absent
    AsyncConnectionPool = None  # type: ignore[assignment]


_pool: Optional[Any] = None


def _read_secret(path: Optional[str]) -> Optional[str]:
    """Read a Docker secret from disk, trimming the trailing newline."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError as exc:
        logger.warning("Could not read secret at %s: %s", path, exc)
        return None


def build_dsn() -> Optional[str]:
    """Assemble a connection string, or None when the app is unconfigured."""
    host = os.getenv("POSTGRES_HOST")
    if not host:
        return None

    password = os.getenv("POSTGRES_PASSWORD") or _read_secret(
        os.getenv("POSTGRES_PASSWORD_FILE")
    )
    if not password:
        logger.warning("POSTGRES_HOST is set but no password is available")
        return None

    user = os.getenv("POSTGRES_USER", "portfolio_user")
    database = os.getenv("POSTGRES_DB", "portfolio")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"host={host} port={port} dbname={database} user={user} password={password}"


SCHEMA = """
CREATE TABLE IF NOT EXISTS contact_submissions (
    id            BIGSERIAL PRIMARY KEY,
    public_id     TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    subject       TEXT,
    message       TEXT NOT NULL,
    notified      BOOLEAN NOT NULL DEFAULT FALSE,
    source_ip     TEXT,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS contact_submissions_created_idx
    ON contact_submissions (created_at DESC);

CREATE TABLE IF NOT EXISTS waitlist_signups (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL,
    product       TEXT NOT NULL DEFAULT 'reseller',
    referrer      TEXT,
    source_ip     TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT waitlist_unique_email_product UNIQUE (email, product)
);
CREATE INDEX IF NOT EXISTS waitlist_created_idx
    ON waitlist_signups (created_at DESC);

CREATE TABLE IF NOT EXISTS blog_posts (
    id            BIGSERIAL PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    summary       TEXT,
    body          TEXT NOT NULL,
    published     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS blog_published_idx
    ON blog_posts (published, created_at DESC);
"""


async def init_pool() -> bool:
    """Open the pool and ensure the tables exist. Returns True on success."""
    global _pool

    if AsyncConnectionPool is None:
        logger.info("psycopg not installed - running without durable storage")
        return False

    dsn = build_dsn()
    if not dsn:
        logger.info("No database configured - running without durable storage")
        return False

    try:
        _pool = AsyncConnectionPool(dsn, min_size=1, max_size=4, open=False)
        await _pool.open(wait=True, timeout=10)
        async with _pool.connection() as conn:
            await conn.execute(SCHEMA)
        logger.info("Durable storage ready")
        return True
    except Exception as exc:
        logger.error("Database unavailable, continuing without it: %s", exc)
        _pool = None
        return False


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def is_available() -> bool:
    return _pool is not None


async def save_contact(
    public_id: str,
    name: str,
    email: str,
    subject: Optional[str],
    message: str,
    notified: bool,
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    """Persist one enquiry. Returns False if it could not be stored."""
    if _pool is None:
        return False
    try:
        async with _pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO contact_submissions
                    (public_id, name, email, subject, message, notified,
                     source_ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (public_id, name, email, subject, message, notified,
                 source_ip, user_agent),
            )
        return True
    except Exception as exc:
        logger.error("Failed to store contact submission %s: %s", public_id, exc)
        return False


async def add_waitlist(
    email: str,
    product: str = "reseller",
    referrer: Optional[str] = None,
    source_ip: Optional[str] = None,
) -> str:
    """Add a signup. Returns 'added', 'duplicate', or 'unavailable'."""
    if _pool is None:
        return "unavailable"
    try:
        async with _pool.connection() as conn:
            cur = await conn.execute(
                """
                INSERT INTO waitlist_signups (email, product, referrer, source_ip)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT waitlist_unique_email_product DO NOTHING
                RETURNING id
                """,
                (email, product, referrer, source_ip),
            )
            row = await cur.fetchone()
        # Already on the list is a success from the visitor's point of view.
        return "added" if row else "duplicate"
    except Exception as exc:
        logger.error("Failed to add waitlist signup: %s", exc)
        return "unavailable"


async def waitlist_count(product: str = "reseller") -> Optional[int]:
    if _pool is None:
        return None
    try:
        async with _pool.connection() as conn:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM waitlist_signups WHERE product = %s",
                (product,),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0
    except Exception as exc:
        logger.error("Failed to count waitlist: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------

async def list_posts(include_drafts: bool = False) -> list:
    """Newest first. Drafts are only ever returned for the admin view."""
    if _pool is None:
        return []
    try:
        async with _pool.connection() as conn:
            if include_drafts:
                cur = await conn.execute(
                    "SELECT slug, title, summary, published, created_at "
                    "FROM blog_posts ORDER BY created_at DESC"
                )
            else:
                cur = await conn.execute(
                    "SELECT slug, title, summary, published, created_at "
                    "FROM blog_posts WHERE published = TRUE ORDER BY created_at DESC"
                )
            rows = await cur.fetchall()
        return [
            {
                "slug": r[0], "title": r[1], "summary": r[2],
                "published": r[3], "created_at": r[4].isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("Failed to list posts: %s", exc)
        return []


async def get_post(slug: str, include_drafts: bool = False) -> Optional[dict]:
    if _pool is None:
        return None
    try:
        async with _pool.connection() as conn:
            sql = ("SELECT slug, title, summary, body, published, created_at "
                   "FROM blog_posts WHERE slug = %s")
            if not include_drafts:
                sql += " AND published = TRUE"
            cur = await conn.execute(sql, (slug,))
            r = await cur.fetchone()
        if not r:
            return None
        return {
            "slug": r[0], "title": r[1], "summary": r[2], "body": r[3],
            "published": r[4], "created_at": r[5].isoformat(),
        }
    except Exception as exc:
        logger.error("Failed to get post %s: %s", slug, exc)
        return None


async def upsert_post(slug: str, title: str, summary: Optional[str],
                      body: str, published: bool) -> bool:
    if _pool is None:
        return False
    try:
        async with _pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO blog_posts (slug, title, summary, body, published)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    body = EXCLUDED.body,
                    published = EXCLUDED.published,
                    updated_at = now()
                """,
                (slug, title, summary, body, published),
            )
        return True
    except Exception as exc:
        logger.error("Failed to save post %s: %s", slug, exc)
        return False


async def delete_post(slug: str) -> bool:
    if _pool is None:
        return False
    try:
        async with _pool.connection() as conn:
            await conn.execute("DELETE FROM blog_posts WHERE slug = %s", (slug,))
        return True
    except Exception as exc:
        logger.error("Failed to delete post %s: %s", slug, exc)
        return False
