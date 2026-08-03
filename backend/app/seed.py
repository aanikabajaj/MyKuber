"""Seed demo accounts and historical analytics data (idempotent)."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.logging_config import get_logger
from app.core.security import hash_secret
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.services.totp_service import encrypt_secret, generate_secret

logger = get_logger("iaare.seed")


def _demo_embedding() -> list:
    rng = random.Random(42)
    return [round(rng.uniform(-1, 1), 4) for _ in range(64)]


DEMO_USERS = [
    dict(username="admin", first="Aarav", last="Sharma", email="admin@psb.bank",
         mobile="+919000000001", password="Admin@1234", mpin="123456",
         city="New Delhi", state="Delhi", country="India", is_admin=True),
    dict(username="rahul", first="Rahul", last="Verma", email="rahul@example.com",
         mobile="+919000000002", password="Rahul@1234", mpin="654321",
         city="Mumbai", state="Maharashtra", country="India", is_admin=False),
    dict(username="priya", first="Priya", last="Nair", email="priya@example.com",
         mobile="+919000000003", password="Priya@1234", mpin="112233",
         city="Bengaluru", state="Karnataka", country="India", is_admin=False),
]

# (city, country, lat, lon)
LOCATIONS = [
    ("New Delhi", "India", 28.6139, 77.2090),
    ("Mumbai", "India", 19.0760, 72.8777),
    ("Bengaluru", "India", 12.9716, 77.5946),
    ("London", "United Kingdom", 51.5074, -0.1278),
    ("New York", "United States", 40.7128, -74.0060),
    ("Moscow", "Russia", 55.7558, 37.6173),
    ("Lagos", "Nigeria", 6.5244, 3.3792),
    ("Frankfurt", "Germany", 50.1109, 8.6821),
]

BANDS = ["SAFE", "SAFE", "SAFE", "MEDIUM", "MEDIUM", "HIGH", "CRITICAL"]


def seed_all() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first():
            logger.info("Seed: demo data already present, skipping.")
            return

        created_users = []
        for idx, spec in enumerate(DEMO_USERS):
            user = User(
                first_name=spec["first"], last_name=spec["last"],
                email=spec["email"], mobile=spec["mobile"],
                username=spec["username"], password_hash=hash_secret(spec["password"]),
                mpin_hash=hash_secret(spec["mpin"]),
                city=spec["city"], state=spec["state"], country=spec["country"],
                totp_secret_enc=encrypt_secret(generate_secret()), totp_enabled=True,
                face_embedding_enc=None, face_enabled=True, second_factor="face",
                email_verified=True, mobile_verified=True,
                registration_stage="complete",
                account_number=f"PSB{50100000000 + idx}",
                balance=[520000.0, 148500.0, 92750.0][idx % 3],
                is_admin=spec["is_admin"], is_demo=True, is_active=True,
            )
            from app.core.encryption import encrypt_json
            user.face_embedding_enc = encrypt_json(_demo_embedding())
            db.add(user)
            created_users.append(user)
        db.commit()
        for u in created_users:
            db.refresh(u)

        # Sample transaction history for the demo accounts
        from app.models.transaction import Transaction as _Txn
        _payees = [("Amazon Pay", "9012xxxx3311", 2499.0), ("Rent - Landlord", "5566xxxx0192", 18000.0),
                   ("Ravi Kumar", "3021xxxx7788", 5000.0), ("Electricity Board", "1122xxxx9900", 1340.0),
                   ("Mutual Fund SIP", "8899xxxx1200", 10000.0)]
        for u in created_users:
            for pi, (pname, pacc, pamt) in enumerate(_payees):
                db.add(_Txn(
                    user_id=u.id, beneficiary_name=pname, beneficiary_account=pacc,
                    amount=pamt, note="Demo transaction", status="completed",
                    step_up_required=pamt >= u.txn_face_threshold,
                    step_up_factor="face" if pamt >= u.txn_face_threshold else None,
                    reference=f"TXN{u.id:02d}{pi:02d}{random.randint(1000,9999)}",
                    balance_after=u.balance, completed_at=datetime.now(timezone.utc),
                ))
        db.commit()

        # A trusted device for the admin (so same-browser demo logins read SAFE)
        admin = created_users[0]
        db.add(Device(
            user_id=admin.id, fingerprint="seed-admin-device",
            label="Seed workstation", browser="Chrome", os="Windows",
            timezone="Asia/Kolkata", language="en-IN", screen_resolution="1920x1080",
            is_trusted=True,
        ))

        # Historical login attempts across the fleet for dashboard richness
        now = datetime.now(timezone.utc)
        rng = random.Random(7)
        for i in range(60):
            loc = rng.choice(LOCATIONS)
            band = rng.choice(BANDS)
            user = rng.choice(created_users)
            success = band != "CRITICAL" and rng.random() > 0.15
            decision = "BLOCK" if band == "CRITICAL" else ("ALLOW" if success else "DENY")
            score = {"SAFE": rng.randint(5, 30), "MEDIUM": rng.randint(31, 60),
                     "HIGH": rng.randint(61, 80), "CRITICAL": rng.randint(81, 99)}[band]
            db.add(LoginAttempt(
                user_id=user.id, username=user.username,
                ip_address=f"{rng.randint(11,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
                country=loc[1], city=loc[0], latitude=loc[2], longitude=loc[3],
                is_vpn=band in ("HIGH", "CRITICAL") and rng.random() > 0.5,
                risk_score=score, risk_band=band, decision=decision, success=success,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                created_at=now - timedelta(hours=rng.randint(0, 168), minutes=rng.randint(0, 59)),
            ))

        db.add(AuditLog(
            user_id=admin.id, event_type="system_seed",
            description="Demo dataset seeded (3 users, 60 login events).",
            severity="info", ip_address="127.0.0.1",
        ))
        db.commit()
        logger.info("Seed: created %d demo users + 60 login events.", len(created_users))
    finally:
        db.close()


if __name__ == "__main__":
    from app.core.database import init_db
    init_db()
    seed_all()
