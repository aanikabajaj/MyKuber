"""Unit tests for IAARE core security & engine logic (no server required)."""
import pyotp

from app.core.security import (
    create_access_token, decode_token, generate_numeric_otp,
    hash_otp, hash_secret, verify_otp, verify_secret,
)
from app.core.encryption import decrypt_json, encrypt_json
from app.services import face_service, totp_service
from app.services.risk_engine import BAND_STEPS, band_for_score
from app.services import captcha_service


def test_password_hash_roundtrip():
    h = hash_secret("Str0ng@Pass1")
    assert h != "Str0ng@Pass1"
    assert verify_secret("Str0ng@Pass1", h)
    assert not verify_secret("wrong", h)


def test_mpin_hash():
    h = hash_secret("123456")
    assert verify_secret("123456", h)
    assert not verify_secret("654321", h)


def test_otp_hash_and_generate():
    code = generate_numeric_otp(6)
    assert len(code) == 6 and code.isdigit()
    h = hash_otp(code)
    assert verify_otp(code, h)
    assert not verify_otp("000000" if code != "000000" else "111111", h)


def test_jwt_roundtrip():
    tok = create_access_token("42", is_admin=True)
    payload = decode_token(tok)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert payload["is_admin"] is True
    assert decode_token("garbage") is None


def test_risk_band_mapping():
    assert band_for_score(0) == "SAFE"
    assert band_for_score(30) == "SAFE"
    assert band_for_score(31) == "MEDIUM"
    assert band_for_score(60) == "MEDIUM"
    assert band_for_score(61) == "HIGH"
    assert band_for_score(80) == "HIGH"
    assert band_for_score(81) == "CRITICAL"
    assert band_for_score(100) == "CRITICAL"


def test_band_steps_escalate():
    assert BAND_STEPS["SAFE"] == ["mpin", "second_factor"]
    assert "email_otp" in BAND_STEPS["MEDIUM"]
    assert "sms_otp" in BAND_STEPS["HIGH"] and "totp" in BAND_STEPS["HIGH"]
    assert BAND_STEPS["CRITICAL"] == []


def test_totp_verify():
    secret = totp_service.generate_secret()
    enc = totp_service.encrypt_secret(secret)
    token = pyotp.TOTP(secret).now()
    assert totp_service.verify_token(enc, token)
    assert not totp_service.verify_token(enc, "000000")


def test_face_match():
    emb = [float(i % 5) - 2 for i in range(64)]
    enc = face_service.encrypt_embedding(emb)
    ok, sim = face_service.compare(enc, emb)
    assert ok and sim > 0.99
    ok2, _ = face_service.compare(enc, [(-v) for v in emb])
    assert not ok2


def test_encryption_roundtrip():
    data = {"a": 1, "b": [1.0, 2.0, 3.0]}
    assert decrypt_json(encrypt_json(data)) == data


def test_captcha_demo_bypass():
    # demo-bypass works while DEMO_MODE is on (default)
    assert captcha_service.verify("demo-bypass", "anything")
    # a real, unknown id fails
    assert not captcha_service.verify("nonexistent-id", "abc")
