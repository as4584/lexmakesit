"""Temporary blocking for clients that keep tripping the rate limits.

Why not fail2ban: this origin publishes no internet-facing port. Every
request arrives through the Cloudflare Tunnel, so the TCP peer is always
the cloudflared container. A tool that bans source IPs would either ban
nothing or ban every visitor at once. The genuine client address exists
only in CF-Connecting-IP, which is visible here and nowhere lower in the
stack, so the ban belongs in the application.

This is a second line of defence, not the first. Cloudflare's own rate
limiting should stop abuse before it reaches the tunnel at all; this
catches what gets through and stops it consuming request handlers.

Deliberately conservative: only /api/ paths count, the thresholds are
generous, and a block expires by itself. Nothing here can permanently
lock anyone out, and a restart clears it entirely.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque, Dict, Tuple

logger = logging.getLogger(__name__)

# A client gets this many rate-limit rejections inside the window before
# it is set aside for a while.
STRIKE_THRESHOLD = 10
STRIKE_WINDOW_SECONDS = 600      # 10 minutes
BLOCK_SECONDS = 900              # 15 minutes

# Hard ceiling on tracked clients so a spoofed-header flood cannot grow
# this table without bound. Oldest entries are evicted first.
MAX_TRACKED = 5000

_strikes: Dict[str, Deque[float]] = {}
_blocked: Dict[str, float] = {}


def _evict_if_needed(table: dict) -> None:
    if len(table) <= MAX_TRACKED:
        return
    # Drop roughly the oldest tenth rather than clearing everything.
    overflow = len(table) - MAX_TRACKED + (MAX_TRACKED // 10)
    for key in list(table.keys())[:overflow]:
        table.pop(key, None)


def is_blocked(client: str) -> Tuple[bool, int]:
    """Return (blocked, seconds_remaining)."""
    until = _blocked.get(client)
    if until is None:
        return False, 0
    remaining = int(until - time.time())
    if remaining <= 0:
        _blocked.pop(client, None)
        _strikes.pop(client, None)
        return False, 0
    return True, remaining


def record_strike(client: str) -> bool:
    """Note one rate-limit rejection. Returns True if this caused a block."""
    now = time.time()
    hits = _strikes.setdefault(client, deque())
    hits.append(now)

    cutoff = now - STRIKE_WINDOW_SECONDS
    while hits and hits[0] < cutoff:
        hits.popleft()

    _evict_if_needed(_strikes)

    if len(hits) >= STRIKE_THRESHOLD:
        _blocked[client] = now + BLOCK_SECONDS
        _strikes.pop(client, None)
        _evict_if_needed(_blocked)
        logger.warning(
            "Client %s blocked for %ss after %s rate-limit rejections in %ss",
            client, BLOCK_SECONDS, STRIKE_THRESHOLD, STRIKE_WINDOW_SECONDS,
        )
        return True
    return False


def stats() -> dict:
    now = time.time()
    active = sum(1 for until in _blocked.values() if until > now)
    return {
        "tracked_clients": len(_strikes),
        "blocked_clients": active,
        "strike_threshold": STRIKE_THRESHOLD,
        "window_seconds": STRIKE_WINDOW_SECONDS,
        "block_seconds": BLOCK_SECONDS,
    }
