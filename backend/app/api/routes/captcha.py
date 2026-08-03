"""CAPTCHA generation endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.auth import CaptchaOut
from app.services import captcha_service

router = APIRouter(prefix="/api/captcha", tags=["captcha"])


@router.get("", response_model=CaptchaOut)
def get_captcha() -> CaptchaOut:
    captcha_id, image = captcha_service.new_captcha()
    return CaptchaOut(captcha_id=captcha_id, image=image)


@router.get("/math")
def get_math_captcha() -> dict:
    captcha_id, question = captcha_service.new_math_captcha()
    return {"captcha_id": captcha_id, "question": question}
