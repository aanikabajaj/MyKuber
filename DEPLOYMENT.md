# IAARE Deployment Guide

IAARE (Intelligent Adaptive Authentication & Risk Engine) — Punjab & Sind Bank

---

## Quick Local Demo (auth stack only, no GPU needed)

Run only the backend + frontend. No AI services, no GPU required.

```bash
docker compose up backend frontend
```

Visit **http://localhost:5173**

The backend API docs are at **http://localhost:8000/docs**

---

## Full Stack with AI

### Option A — With NVIDIA GPU

Requires Docker with the NVIDIA Container Toolkit installed.

```bash
docker compose up --build
```

Services started:
- `backend` — IAARE FastAPI auth backend (port 8000)
- `frontend` — Vite/React web app (port 5173)
- `ai_gateway` — AI financial advisor gateway (port 8001)
- `celery_worker` — Background RAG ingestion worker
- `vllm` — Qwen3-8B LLM inference (port 8002, GPU required)
- `qdrant` — Vector store (port 6333)
- `redis` — Cache + Celery broker (port 6379)
- `ai_postgres` — AI-specific database (port 5433)
- `minio` — Object storage for RAG documents (ports 9000/9001)

### Option B — Without GPU (CPU fallback via Ollama)

1. Comment out the `vllm` service in `docker-compose.yml`
2. Install [Ollama](https://ollama.com) on your host machine
3. Pull a small model: `ollama pull llama3.2:3b`
4. Ollama exposes an OpenAI-compatible API at `http://host.docker.internal:11434/v1`
5. In `docker-compose.yml`, change the `ai_gateway` environment:

```yaml
VLLM_BASE_URL: "http://host.docker.internal:11434/v1"
```

6. Start without vllm:

```bash
docker compose up backend frontend ai_gateway celery_worker redis ai_postgres qdrant minio
```

> Note: CPU inference is significantly slower. Expect 30–90s per response on a typical laptop.

---

## Mobile App Setup

The React Native / Expo mobile app runs natively — it is NOT containerised.

### Step 1 — Find your LAN IP

```bash
# Windows
ipconfig

# macOS / Linux
ifconfig
```

Look for your WiFi adapter's IPv4 address (e.g. `192.168.1.10`).

### Step 2 — Configure mobile environment

Edit `mobile/.env`:

```env
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
EXPO_PUBLIC_AI_URL=http://192.168.1.10:8001
```

> Android emulator: use `http://10.0.2.2:8000` instead of the LAN IP.
> iOS Simulator: use `http://localhost:8000`.

### Step 3 — Start Expo

```bash
cd mobile
npx expo start
```

### Step 4 — Open on device

- Install **Expo Go** from the App Store or Play Store
- Scan the QR code shown in the terminal
- Or press `w` for Expo web preview at **http://localhost:8081**
- Or press `a` / `i` for Android / iOS emulator

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `IAARE_SECRET_KEY` | JWT signing secret — **change in production** | `iaare-dev-secret-key-...` |
| `IAARE_DEMO_MODE` | Enables pre-seeded demo accounts | `true` |
| `IAARE_DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./iaare.db` |
| `IAARE_RP_ID` | WebAuthn relying party domain | `localhost` |
| `IAARE_EXPECTED_ORIGIN` | WebAuthn origin (must match browser URL) | `http://localhost:5173` |
| `IAARE_CORS_ORIGINS` | Comma-separated allowed CORS origins | see file |
| `IAARE_SMTP_HOST` | SMTP server for OTP emails (optional) | *(empty)* |
| `IAARE_TWILIO_ACCOUNT_SID` | Twilio SID for SMS OTPs (optional) | *(empty)* |
| `IAARE_GEOIP_ENABLED` | Enable GeoIP risk scoring | `true` |

### AI Gateway (`ai/.env`)

| Variable | Description | Default |
|---|---|---|
| `IAARE_SECRET_KEY` | Must match backend secret (shared JWT verification) | `iaare-dev-secret-key-...` |
| `IAARE_DATABASE_URL` | Path to IAARE backend SQLite DB (read-only) | `sqlite:////app/iaare.db` |
| `AI_DATABASE_URL` | AI-specific PostgreSQL database | see file |
| `VLLM_BASE_URL` | OpenAI-compatible LLM endpoint | `http://vllm:8000/v1` |
| `QDRANT_URL` | Qdrant vector store endpoint | `http://qdrant:6333` |
| `REDIS_URL` | Redis connection for caching | `redis://redis:6379/0` |
| `MINIO_ENDPOINT` | MinIO object storage endpoint | `minio:9000` |

### Mobile (`mobile/.env`)

| Variable | Description | Default |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | IAARE backend URL from device | *(auto)* |
| `EXPO_PUBLIC_AI_URL` | AI gateway URL from device | *(auto)* |

---

## Demo Accounts

These accounts are pre-seeded in demo mode (`IAARE_DEMO_MODE=true`):

| Username | Password | Role | Notes |
|---|---|---|---|
| `admin` | `Admin@1234` | Administrator | Full access |
| `rahul` | `Rahul@1234` | Customer | Sample transactions |
| `priya` | `Priya@1234` | Customer | Sample transactions |

---

## Cloud Deployment (Single VM)

### Ports to open in your firewall / security group

| Port | Service |
|---|---|
| 5173 | Frontend (Vite) |
| 8000 | IAARE Backend API |
| 8001 | AI Gateway |
| 6333 | Qdrant (restrict to internal only in production) |
| 6379 | Redis (restrict to internal only in production) |

### nginx Reverse Proxy Config

Install nginx and use the following config to expose everything under one domain:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # AI Gateway
    location /ai/ {
        proxy_pass http://localhost:8001/ai/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

For production, add SSL with Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Production Checklist

- [ ] Change `IAARE_SECRET_KEY` to a strong random value (e.g. `openssl rand -hex 32`)
- [ ] Set `IAARE_DEMO_MODE=false`
- [ ] Use PostgreSQL instead of SQLite for the backend DB
- [ ] Restrict CORS origins to your actual domain
- [ ] Set real SMTP credentials for email OTPs
- [ ] Set real Twilio credentials for SMS OTPs
- [ ] Restrict Redis and Qdrant ports to internal network only
- [ ] Enable HTTPS (Certbot or load balancer SSL termination)
- [ ] Update `IAARE_RP_ID` and `IAARE_EXPECTED_ORIGIN` to your production domain
