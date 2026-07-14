<div align="center">

# 🛡️ IAARE
### Intelligent Adaptive Authentication & Risk Assessment Engine
**Next-Generation Adaptive Banking Authentication Prototype — Punjab & Sind Bank Hackathon**

</div>

---

> **This is a high-fidelity working demonstration prototype, not a production banking system.**
> Every feature is functional end-to-end. SMS/Email delivery is abstracted behind a provider
> interface — add credentials to go live; otherwise codes are surfaced in demo mode.

IAARE reimagines banking login as a **risk-aware decision** rather than a fixed checklist. Every
login is scored 0–100 from device, network, geography and behavioural signals, and the required
authentication factors **scale up or down with the threat** of that specific attempt.

## ✨ Features

| Area | What it does |
|---|---|
| **Adaptive Risk Engine** | Transparent 0–100 score with a full per-factor breakdown, mapped to SAFE / MEDIUM / HIGH / CRITICAL bands |
| **Step-Up Authentication** | SAFE → MPIN + Face/Passkey · MEDIUM → + Email OTP · HIGH → + SMS OTP + Authenticator · CRITICAL → blocked |
| **Full MFA Stack** | Password, 6-digit MPIN, Email OTP, SMS OTP, Google Authenticator (TOTP) |
| **Biometric / Passkey** | Face verification **or** FIDO2/WebAuthn passkeys (Windows Hello, Touch ID, security keys) |
| **Device Intelligence** | Browser fingerprinting, trusted-device tracking |
| **Geo / Threat** | GeoIP lookup, VPN/proxy detection, impossible-travel (geo-velocity) checks |
| **Admin Command Center** | Risk distribution, auth statistics, 7-day trend, global login map, login & audit tables |
| **Security** | bcrypt hashing, JWT access/refresh, Fernet-encrypted secrets at rest, audit logging, rate limiting, server-rendered CAPTCHA |

## 🧱 Tech Stack

**Frontend** — React 19 · TypeScript · Vite · Tailwind CSS · Recharts · React Router · Axios · React Hook Form · Zod · Framer Motion
**Backend** — Python · FastAPI · SQLAlchemy · Pydantic · JWT · bcrypt · PyOTP · py_webauthn · Cryptography
**Database** — SQLite (dev) · **Deployment** — Docker & Docker Compose (optional)

## 🚀 Quick Start (local — recommended for the demo)

**Prerequisites:** Python 3.10+ and Node.js 18+.

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt        # add --trusted-host pypi.org --trusted-host files.pythonhosted.org behind TLS-intercepting networks
uvicorn app.main:app --reload --port 8000
```
The database is created and seeded automatically on first start. API docs live at **http://localhost:8000/docs**.

### 2. Frontend (new terminal)
```bash
cd frontend
npm install                             # add --strict-ssl=false behind TLS-intercepting networks
npm run dev
```
Open **http://localhost:5173**.

> One-shot helpers are provided at the repo root: **`./run.ps1`** (Windows) or **`./run.sh`** (macOS/Linux).

## 🔑 Demo Accounts

| Username | Password | MPIN | Role |
|---|---|---|---|
| `admin` | `Admin@1234` | `123456` | Admin |
| `rahul` | `Rahul@1234` | `654321` | Customer |
| `priya` | `Priya@1234` | `112233` | Customer |

Seeded demo accounts use **Face** as their strong factor and auto-pass the biometric step in demo
mode (so they log in on any machine without the enrolled face). **Newly registered accounts use
genuine face-embedding matching or real passkeys.**

## 🎬 Demo Script

1. **Register a new account** → mobile OTP → email OTP → Google Authenticator (scan the QR) → MPIN → choose Face **or** Passkey → success. *(OTP codes are shown on-screen in demo mode.)*
2. **Log in** as your new user from the same browser → **SAFE** band → MPIN + Face/Passkey → dashboard.
3. Open the **Demo Console** on the login page and arm **MEDIUM / HIGH / CRITICAL** (or toggle VPN, new device, foreign country, failed attempts) to watch the factor chain adapt — and CRITICAL get blocked.
4. Log in as **admin** → **Admin Command Center**: risk charts, global login map, live login & audit tables.

## 🔌 Going Live (real SMS / Email)

Everything runs without any `.env`. To enable real delivery, copy `backend/.env.example` to
`backend/.env` and fill in:
- **Email** — `IAARE_SMTP_HOST/PORT/USER/PASSWORD`
- **SMS** — `IAARE_TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_NUMBER`

Set `IAARE_DEMO_MODE=false` to stop surfacing OTP codes and disable demo shortcuts. No other code changes are required — delivery is isolated in `app/services/notification_service.py`.

## 🐳 Docker (optional)
```bash
docker compose up --build
# frontend → http://localhost:5173   backend → http://localhost:8000
```

## 📚 Documentation
- [docs/INSTALLATION.md](docs/INSTALLATION.md) — full setup & troubleshooting
- [docs/API.md](docs/API.md) — REST API reference
- [docs/DEMO.md](docs/DEMO.md) — presenter script & credentials
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design & folder structure

## 📁 Folder Structure
```
IAARE/
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── core/           # config, db, security, encryption, rate limiting
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # risk engine, OTP, TOTP, WebAuthn, geoip, face, captcha…
│   │   ├── api/routes/     # captcha, registration, login, auth, user, admin
│   │   ├── main.py         # app assembly
│   │   └── seed.py         # demo data seeding
│   └── requirements.txt
├── frontend/               # React + Vite + TypeScript
│   └── src/
│       ├── components/     # UI primitives, layout, feature components
│       ├── pages/          # Landing, About, Register, Login, Dashboard, Settings, Admin
│       ├── context/        # auth context
│       └── lib/            # api client, fingerprint, face embedding, webauthn
├── docs/
├── docker-compose.yml
├── run.ps1 / run.sh
└── README.md
```

---
<div align="center"><sub>Built for the Punjab &amp; Sind Bank Hackathon · Demonstration prototype</sub></div>
