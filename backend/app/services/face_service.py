"""Face verification.

Primary path: OpenCV **SFace** deep face recognition (YuNet detector + SFace
recognizer, ONNX models under ``backend/models/``). This produces a 128-dim
discriminative embedding per face and matches with a strict cosine threshold —
so different people are reliably rejected (iPhone-Face-ID-style behaviour).

Fallback path: if the models/OpenCV are unavailable, a lightweight pixel
embedding is used so the app still runs (less accurate — accepts similar faces).
"""
from __future__ import annotations

import base64
import math
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from app.core.encryption import decrypt_json, encrypt_json
from app.core.logging_config import get_logger

logger = get_logger("iaare.face")

# --- Thresholds ---------------------------------------------------------- #
# SFace cosine similarity: >= threshold means SAME identity. 0.363 is the
# OpenCV-recommended operating point; we nudge it up slightly for strictness.
SFACE_THRESHOLD = 0.38
# Legacy pixel-embedding fallback (only used if SFace can't load).
PIXEL_THRESHOLD = 0.22

_GRID = 12
_CROP = 0.7

# --- SFace model loading (lazy, once) ------------------------------------ #
_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_detector = None
_recognizer = None
_sface_ready: Optional[bool] = None


def _load_sface() -> bool:
    global _detector, _recognizer, _sface_ready
    if _sface_ready is not None:
        return _sface_ready
    try:
        import cv2

        yunet = str(_MODELS_DIR / "yunet.onnx")
        sface = str(_MODELS_DIR / "sface.onnx")
        _detector = cv2.FaceDetectorYN.create(yunet, "", (320, 320), 0.7, 0.3, 5000)
        _recognizer = cv2.FaceRecognizerSF.create(sface, "")
        _sface_ready = True
        logger.info("SFace face recognition ready (deep model loaded).")
    except Exception as exc:  # noqa: BLE001
        _sface_ready = False
        logger.warning("SFace unavailable (%s) — falling back to pixel embeddings.", exc)
    return _sface_ready


def sface_available() -> bool:
    return _load_sface()


# --- Storage helpers ----------------------------------------------------- #
def encrypt_embedding(embedding: List[float]) -> str:
    return encrypt_json([embedding])


def encrypt_templates(templates: List[List[float]]) -> str:
    clean = [t for t in templates if t]
    return encrypt_json(clean)


# --- Embedding computation ---------------------------------------------- #
def _decode_b64(b64_str: str) -> Optional[bytes]:
    if not b64_str:
        return None
    if "," in b64_str[:64]:  # strip a data-URI prefix if present
        b64_str = b64_str.split(",", 1)[1]
    try:
        return base64.b64decode(b64_str)
    except Exception:  # noqa: BLE001
        return None


def _sface_embedding(raw: bytes) -> List[float]:
    """Detect the largest face and return its 128-dim SFace embedding, or []."""
    import cv2
    import numpy as np

    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return []
    h, w = img.shape[:2]
    _detector.setInputSize((w, h))
    _, faces = _detector.detect(img)
    if faces is None or len(faces) == 0:
        return []
    # pick the largest detected face (w*h)
    face = max(faces, key=lambda f: float(f[2]) * float(f[3]))
    aligned = _recognizer.alignCrop(img, face)
    feat = _recognizer.feature(aligned)
    return [round(float(x), 6) for x in feat.flatten()]


def _pixel_embedding(raw: bytes) -> List[float]:
    """Lightweight fallback: center-crop -> 12x12 grayscale -> mean/std norm."""
    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:  # noqa: BLE001
        return []
    w, h = img.size
    side = int(min(w, h) * _CROP) or 1
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((_GRID, _GRID))
    pixels = list(img.getdata())
    gray = [(r * 0.299 + g * 0.587 + b * 0.114) / 255.0 for (r, g, b) in pixels]
    mean = sum(gray) / len(gray)
    var = sum((x - mean) ** 2 for x in gray) / len(gray)
    std = math.sqrt(var) or 1.0
    return [round((x - mean) / std, 4) for x in gray]


def embedding_from_image_b64(b64_str: str) -> List[float]:
    """Return a face embedding for a base64 image. Empty list = no usable face."""
    raw = _decode_b64(b64_str)
    if raw is None:
        return []
    if _load_sface():
        return _sface_embedding(raw)
    return _pixel_embedding(raw)


def embeddings_from_images(images: List[str]) -> List[List[float]]:
    out: List[List[float]] = []
    for im in images:
        e = embedding_from_image_b64(im)
        if e:
            out.append(e)
    return out


# --- Matching ------------------------------------------------------------ #
def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _as_templates(stored) -> List[List[float]]:
    if not stored:
        return []
    if isinstance(stored[0], (int, float)):
        return [stored]
    return stored


def compare(encrypted_embedding: Optional[str], candidate: List[float]) -> Tuple[bool, float]:
    """Match the candidate against every enrolled template; accept the best.

    Threshold depends on the embedding type: 128-dim = SFace (strict), otherwise
    the legacy pixel embedding. Only same-dimension templates are compared.
    """
    stored = decrypt_json(encrypted_embedding) if encrypted_embedding else None
    templates = _as_templates(stored)
    if not templates or not candidate:
        return False, 0.0
    dim = len(candidate)
    threshold = SFACE_THRESHOLD if dim == 128 else PIXEL_THRESHOLD
    sims = [_cosine(t, candidate) for t in templates if len(t) == dim]
    if not sims:
        return False, 0.0
    best = max(sims)
    return best >= threshold, round(best, 4)
