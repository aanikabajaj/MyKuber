"""Very small in-memory sliding-window rate limiter (per client IP)."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from app.core.config import settings

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def allow(key: str) -> bool:
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    bucket = _hits[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_MAX_REQUESTS:
        return False
    bucket.append(now)
    return True
