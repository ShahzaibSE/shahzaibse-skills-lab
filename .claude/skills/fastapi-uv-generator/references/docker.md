# Docker Best Practices

## Multi-Stage Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Build dependencies
# ============================================
FROM python:3.12-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source and install project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim as runtime

# Create non-root user
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run application
EXPOSE 8000
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Production Dockerfile (with Gunicorn)

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim as builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
FROM python:3.12-slim as runtime

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash app

# Install gunicorn
RUN pip install --no-cache-dir gunicorn

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app gunicorn.conf.py ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000
CMD ["gunicorn", "src.app.main:app", "-c", "gunicorn.conf.py"]
```

---

## Gunicorn Configuration

```python
# gunicorn.conf.py
import multiprocessing

# Bind
bind = "0.0.0.0:8000"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeouts
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "fastapi-app"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Hooks
def on_starting(server):
    pass

def on_exit(server):
    pass
```

---

## Docker Compose (Development)

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-prod}
      - DEBUG=true
      - ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
    volumes:
      - ./src:/app/src:ro  # Hot reload in dev
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    command: uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Optional: Database admin
  adminer:
    image: adminer
    ports:
      - "8080:8080"
    depends_on:
      - db

volumes:
  postgres_data:
  redis_data:
```

---

## Docker Compose (Production)

```yaml
# docker-compose.prod.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=false
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "1"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 128M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app
    restart: always
```

---

## .dockerignore

```
# Git
.git
.gitignore

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
.venv
venv/
ENV/
.eggs/
*.egg-info/
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Build
dist/
build/
*.manifest
*.spec

# Local config
.env
.env.*
!.env.example

# Docker
Dockerfile*
docker-compose*
.docker/

# Docs
docs/
*.md
!README.md

# Misc
.DS_Store
Thumbs.db
*.log
```

---

## Health Check Endpoint

```python
# src/{project}/main.py
from fastapi import FastAPI, status
from sqlalchemy import text

from .database import async_session

app = FastAPI()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for Docker/Kubernetes."""
    return {"status": "healthy"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness check - verifies database connectivity."""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "database": str(e)}
        )
```

---

## Environment Variables

```bash
# .env.example

# Application
APP_NAME=FastAPI App
DEBUG=false
SECRET_KEY=your-secret-key-min-32-chars-change-this

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Auth
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (comma-separated)
ALLOWED_ORIGINS=https://myapp.com,https://admin.myapp.com

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

---

## Docker Commands Reference

```bash
# Build
docker compose build

# Run development
docker compose up -d

# Run production
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose logs -f app

# Run migrations
docker compose exec app alembic upgrade head

# Shell access
docker compose exec app /bin/bash

# Run tests
docker compose exec app pytest

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v
```
