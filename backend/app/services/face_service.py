"""Face-verification support (prototype-fidelity).

The browser captures a webcam frame and derives a compact, normalised feature
vector (see frontend `faceEmbedding.ts`). We store that vector encrypted at
rest and, on re-authentication, compare via cosine similarity against a
threshold. This is an honest prototype of biometric matching — it demonstrably
enrolls and verifies a face without pretending to be production-grade biometric
security (for which a passkey is offered as the stronger alternative).
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from app.core.encryption import decrypt_json, encrypt_json

# Cosine-similarity acceptance threshold (0..1). Tuned for the frontend
# average-hash style embedding.
MATCH_THRESHOLD = 0.88


def encrypt_embedding(embedding: List[float]) -> str:
    return encrypt_json(embedding)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def compare(encrypted_embedding: Optional[str], candidate: List[float]) -> Tuple[bool, float]:
    stored = decrypt_json(encrypted_embedding) if encrypted_embedding else None
    if not stored or not candidate:
        return False, 0.0
    sim = _cosine(stored, candidate)
    return sim >= MATCH_THRESHOLD, round(sim, 4)
