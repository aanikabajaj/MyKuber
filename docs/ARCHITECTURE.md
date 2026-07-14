# Architecture

## Overview
IAARE is a two-tier application: a **FastAPI** backend exposing a REST API, and a **React (Vite)**
single-page frontend. State lives in **SQLite** via SQLAlchemy. Authentication is **stateless JWT**
(access + refresh), with a short-lived **server-side session** tracking the multi-step adaptive login.

```
┌────────────────────┐        /api/*         ┌──────────────────────────┐
│   React 19 + Vite   │  ───────────────────▶ │        FastAPI           │
│  (Tailwind, Recharts)│  (Vite proxy / nginx) │  routes → services → ORM │
└────────────────────┘                        └──────────────┬───────────┘
                                                              │
                                                       ┌──────▼──────┐
                                                       │   SQLite    │
                                                       └─────────────┘
```

## The adaptive login pipeline
1. **`/api/login/password`** verifies the CAPTCHA and password.
2. The **Risk Engine** (`services/risk_engine.py`) scores the attempt from:
   device trust, VPN/proxy, failed attempts, foreign country, impossible travel (geo-velocity),
   first-login and odd-hour signals — each contributing transparent points.
3. The score maps to a **band** → an **ordered list of required factors**:
   - `SAFE (0-30)` → MPIN, second factor
   - `MEDIUM (31-60)` → + Email OTP
   - `HIGH (61-80)` → + SMS OTP + Authenticator
   - `CRITICAL (81-100)` → blocked
4. An **`AuthSession`** row stores the required/completed steps. Each `/api/login/step/*` call
   advances it; when all factors are satisfied the session is **finalized** — the device is
   trusted, a `LoginAttempt` is recorded, and JWT access/refresh tokens are issued.

## Security model
- **Passwords & MPIN** — bcrypt (SHA-256 pre-hash to avoid the 72-byte limit).
- **TOTP secrets & face embeddings** — Fernet-encrypted at rest (key derived from `SECRET_KEY`).
- **OTP codes** — stored only as salted SHA-256 hashes, single-use, TTL + attempt limits.
- **Passkeys** — real FIDO2/WebAuthn via `py_webauthn`; challenges persisted server-side.
- **JWT** — separate `access`, `refresh` and `register` token types; refresh rotation endpoint.
- **Defence** — per-IP rate limiting, server-rendered image CAPTCHA, full audit log.

## Backend layout
```
app/
├── core/        config · database · security · encryption · rate_limit · logging · utils
├── models/      user · device · otp · auth_session · login_attempt · audit · webauthn
├── schemas/     auth · user · admin  (Pydantic v2)
├── services/    risk_engine · otp · totp · webauthn · geoip · face · device
│                notification (SMS/Email abstraction) · captcha · login · audit
├── api/routes/  captcha · registration · login · auth · user · admin
├── main.py      app assembly, CORS, startup seeding
└── seed.py      demo users + historical analytics
```

## Frontend layout
```
src/
├── lib/         api (typed client) · fingerprint · faceEmbedding · webauthn · utils
├── context/     AuthContext (JWT session state)
├── components/  ui/ (button, card, input, tabs, …) · layout/ · RiskGauge · RiskFactors
│                StepIndicator · FaceCapture · WorldMap · StatCard
└── pages/       Landing · About · Register · Login · Dashboard · Settings · AdminDashboard
```

## Notes on prototype fidelity
- **Face verification** uses a client-computed normalised embedding compared server-side with
  cosine similarity — an honest prototype of biometric matching. A **passkey** is offered as the
  stronger, production-grade alternative.
- **GeoIP** uses the free `ip-api.com` endpoint with graceful offline fallback; a **Demo Console**
  lets a presenter simulate any location/VPN/scenario deterministically.
