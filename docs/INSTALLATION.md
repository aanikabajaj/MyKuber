# Installation Guide

## Prerequisites
- **Python 3.10+**
- **Node.js 18+** (tested on Node 24) and npm
- (Optional) **Docker** + Docker Compose

## 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- The SQLite database (`backend/iaare.db`) is created and **seeded automatically** on first launch.
- Swagger UI: http://localhost:8000/docs

### Behind a TLS-intercepting / corporate network
If `pip` fails with `CERTIFICATE_VERIFY_FAILED`:
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The Vite dev server proxies `/api` → `http://127.0.0.1:8000`.

### Behind a TLS-intercepting network
```bash
npm install --strict-ssl=false
```

## 3. One-shot run scripts (root)
- **Windows:** `./run.ps1`
- **macOS/Linux:** `./run.sh`

These create the venv (if needed), install dependencies, and start both servers.

## 4. Configuration (optional)
Copy `backend/.env.example` → `backend/.env` to enable real SMS/Email and tune settings.
Everything works without it (demo mode).

## Troubleshooting
| Symptom | Fix |
|---|---|
| `pip` / `npm` SSL cert errors | Use the trusted-host / `--strict-ssl=false` flags above |
| Port already in use | Change `--port` (backend) or `server.port` in `vite.config.ts` |
| Camera blocked on face step | Allow camera permission, or choose **Passkey** instead |
| Passkey prompt cancelled | Retry, or use **Face**; passkeys need a platform authenticator (Windows Hello / Touch ID) |
| Want a clean slate | Stop the server and delete `backend/iaare.db`; it re-seeds on next start |
