FROM python:3.11-slim AS base
WORKDIR /app

COPY ai/requirements.txt ./ai/requirements.txt
RUN pip install --no-cache-dir -r ai/requirements.txt

# Copy AI gateway source
COPY ai/ ./ai/

# Copy IAARE backend source so `from app.core.security import decode_token` resolves
COPY backend/ ./backend/

# Ensure both /app (for ai.*) and /app/backend (for app.*) are importable
ENV PYTHONPATH=/app:/app/backend

EXPOSE 8001

# Respect the platform-provided $PORT (Render/Railway/Fly), default 8001 locally.
# Single worker: this process eagerly loads torch/langgraph/cvxpy at startup
# (see main.py's lifespan warmup) — a second worker would load all of that
# a second time, roughly doubling memory for no real benefit at this scale.
CMD ["sh", "-c", "uvicorn ai.main:app --host 0.0.0.0 --port ${PORT:-8001} --workers 1"]
