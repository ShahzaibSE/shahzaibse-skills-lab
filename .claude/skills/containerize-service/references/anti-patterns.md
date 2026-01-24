# Container Anti-Patterns

Common mistakes in Dockerfile design and how to fix them.

---

## Base Image Issues

### Using `latest` Tag

```dockerfile
# BAD
FROM python:latest
FROM node:latest

# GOOD - pinned version
FROM python:3.12.3-slim

# BEST - pinned with digest
FROM python:3.12.3-slim@sha256:abc123...
```

**Why bad:**
- Non-reproducible builds
- Surprise breaking changes
- Different images on different machines

---

### Using Full/Bloated Images

```dockerfile
# BAD - 1GB+ image
FROM python:3.12
FROM ubuntu:22.04

# GOOD - minimal variants
FROM python:3.12-slim    # ~150MB
FROM python:3.12-alpine  # ~50MB
```

**Why bad:**
- Larger attack surface
- More CVEs to patch
- Slower pulls and deploys
- Wasted resources

---

## Build Inefficiencies

### Copying Everything First

```dockerfile
# BAD - any source change invalidates cache
COPY . /app
RUN pip install -r requirements.txt

# GOOD - dependencies cached separately
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app
```

**Why bad:**
- Every code change triggers full dependency reinstall
- Much slower builds

---

### Not Using Lock Files

```dockerfile
# BAD - non-deterministic
RUN pip install flask requests
RUN npm install

# GOOD - locked versions
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY package.json package-lock.json ./
RUN npm ci
```

**Why bad:**
- Different builds get different versions
- "Works on my machine" problems
- Security vulnerabilities introduced silently

---

### Single-Stage Builds

```dockerfile
# BAD - build tools in production image
FROM python:3.12
RUN apt-get install -y build-essential
COPY . /app
RUN pip install .
CMD ["python", "-m", "app"]

# GOOD - multi-stage
FROM python:3.12 AS builder
RUN pip install build
COPY . /build
RUN python -m build

FROM python:3.12-slim
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl
CMD ["python", "-m", "app"]
```

**Why bad:**
- Huge images with compilers, headers, etc.
- Unnecessary attack surface
- Slower deploys

---

### Multiple RUN Commands

```dockerfile
# BAD - creates multiple layers
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y ca-certificates
RUN rm -rf /var/lib/apt/lists/*

# GOOD - single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

**Why bad:**
- More layers = larger image
- Intermediate layers not cleaned up
- `apt-get update` cached incorrectly

---

## Security Issues

### Running as Root

```dockerfile
# BAD - runs as root
FROM python:3.12-slim
COPY . /app
CMD ["python", "app.py"]

# GOOD - non-root user
FROM python:3.12-slim
RUN useradd --system --uid 1001 app
COPY --chown=app:app . /app
USER app
CMD ["python", "app.py"]
```

**Why bad:**
- Container escape gives root access
- Can modify any file in container
- Violates principle of least privilege

---

### Secrets in Image

```dockerfile
# BAD - secrets in ENV
ENV API_KEY=sk-12345abcde
ENV DATABASE_URL=postgres://user:password@host/db

# BAD - secrets in ARG (still visible)
ARG SECRET_KEY
ENV SECRET_KEY=$SECRET_KEY

# BAD - copying secrets file
COPY .env /app/.env
COPY credentials.json /app/

# GOOD - no secrets in image
ENV LOG_LEVEL=info  # Only non-sensitive defaults
# Secrets injected at runtime with -e or --secret
```

**Why bad:**
- Visible in image history (`docker history`)
- Persisted in layer forever
- Exposed if image is leaked
- Cannot rotate without rebuilding

---

### Using ADD Instead of COPY

```dockerfile
# BAD - ADD has surprising behaviors
ADD https://example.com/script.sh /app/
ADD archive.tar.gz /app/

# GOOD - explicit operations
COPY archive.tar.gz /tmp/
RUN tar -xzf /tmp/archive.tar.gz -C /app && rm /tmp/archive.tar.gz

# Download with explicit verification
RUN curl -fsSL https://example.com/script.sh -o /app/script.sh && \
    sha256sum -c <<< "expected_hash  /app/script.sh"
```

**Why bad:**
- ADD auto-extracts archives (unexpected)
- ADD fetches remote URLs (security risk)
- No checksum verification

---

### Installing Without `--no-install-recommends`

```dockerfile
# BAD - installs recommended packages
RUN apt-get install -y curl

# GOOD - minimal install
RUN apt-get install -y --no-install-recommends curl
```

**Why bad:**
- Installs unnecessary packages
- Larger image size
- More CVEs

---

## Configuration Issues

### Hardcoded Configuration

```dockerfile
# BAD - environment-specific values
ENV DATABASE_HOST=prod-db.example.com
ENV API_URL=https://api.production.com
COPY config/production.yaml /app/config.yaml

# GOOD - generic defaults, configured at runtime
ENV DATABASE_HOST=localhost
ENV API_URL=http://localhost:8080
# Config mounted at runtime: -v config.yaml:/app/config.yaml
```

**Why bad:**
- Can't use same image in dev/staging/prod
- Violates 12-factor app principles
- Requires rebuild for config changes

---

### No Health Check

```dockerfile
# BAD - no health check
CMD ["./app"]

# GOOD - health check defined
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
CMD ["./app"]
```

**Why bad:**
- Orchestrators can't detect unhealthy containers
- Failed containers keep receiving traffic
- No automatic recovery

---

## Dockerfile Syntax Issues

### Not Using Syntax Directive

```dockerfile
# BAD - uses old parser
FROM python:3.12

# GOOD - enables BuildKit features
# syntax=docker/dockerfile:1
FROM python:3.12
```

**Why bad:**
- Missing cache mounts
- Missing heredocs
- Missing bind mounts
- Older, slower builds

---

### Shell Form Instead of Exec Form

```dockerfile
# BAD - shell form (runs via /bin/sh -c)
CMD python app.py
ENTRYPOINT ./start.sh

# GOOD - exec form (direct execution)
CMD ["python", "app.py"]
ENTRYPOINT ["./start.sh"]
```

**Why bad:**
- Shell form doesn't receive signals properly
- PID 1 issues with graceful shutdown
- Extra shell process overhead

---

## Quick Reference Table

| Anti-Pattern | Impact | Fix |
|--------------|--------|-----|
| `FROM image:latest` | Non-reproducible | Pin version + digest |
| Full base images | Large, more CVEs | Use slim/alpine/distroless |
| `COPY . .` first | Cache invalidation | Copy deps first |
| No lock files | Non-deterministic | Use and copy lock files |
| Single stage | Bloated runtime | Multi-stage builds |
| Running as root | Security risk | Add USER directive |
| Secrets in ENV/ARG | Exposed credentials | Runtime injection |
| ADD for files | Unpredictable | Use COPY |
| No --no-install-recommends | Bloat | Always use flag |
| Hardcoded config | Not portable | Runtime configuration |
| No HEALTHCHECK | No auto-recovery | Add health check |
| Shell form CMD | Signal issues | Use exec form |
