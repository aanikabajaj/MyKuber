"""Server-generated image CAPTCHA (self-contained, no external service)."""
from __future__ import annotations

import base64
import random
import secrets
import string
import time
from io import BytesIO
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

_CAPTCHA_TTL = 300  # seconds
# captcha_id -> (answer_lower, created_ts)
_store: Dict[str, Tuple[str, float]] = {}

_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"


def _prune() -> None:
    now = time.time()
    expired = [k for k, (_, ts) in _store.items() if now - ts > _CAPTCHA_TTL]
    for k in expired:
        _store.pop(k, None)


def _render(text: str) -> str:
    w, h = 200, 70
    img = Image.new("RGB", (w, h), (16, 22, 40))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()

    # noise lines
    for _ in range(6):
        draw.line(
            [(random.randint(0, w), random.randint(0, h)) for _ in range(2)],
            fill=(random.randint(40, 90), random.randint(60, 120), random.randint(90, 160)),
            width=2,
        )
    # characters, jittered
    x = 18
    for ch in text:
        y = random.randint(8, 22)
        colour = (random.randint(150, 255), random.randint(180, 255), random.randint(200, 255))
        draw.text((x, y), ch, font=font, fill=colour)
        x += 32
    # speckle noise
    for _ in range(500):
        draw.point(
            (random.randint(0, w), random.randint(0, h)),
            fill=(random.randint(30, 90), random.randint(40, 110), random.randint(70, 150)),
        )
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def new_captcha() -> Tuple[str, str]:
    _prune()
    text = "".join(secrets.choice(_ALPHABET) for _ in range(5))
    captcha_id = secrets.token_hex(12)
    _store[captcha_id] = (text.lower(), time.time())
    return captcha_id, _render(text)


def verify(captcha_id: str, answer: str) -> bool:
    # DEMO_MODE-only bypass for automated tests / scripted demos. Disabled when
    # DEMO_MODE is false. The real frontend always solves a rendered captcha.
    from app.core.config import settings
    if settings.DEMO_MODE and captcha_id == "demo-bypass":
        return True

    _prune()
    entry = _store.pop(captcha_id, None)
    if not entry:
        return False
    expected, ts = entry
    if time.time() - ts > _CAPTCHA_TTL:
        return False
    return (answer or "").strip().lower() == expected
