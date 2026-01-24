# Container Security Checklist

Comprehensive security hardening checklist for production container images.

---

## Pre-Build Checklist

### Secrets Management

- [ ] **No secrets in Dockerfile**
  ```dockerfile
  # BAD - secrets visible in layer history
  ENV API_KEY=sk-12345
  ARG DATABASE_PASSWORD
  COPY .env /app/.env

  # GOOD - inject at runtime
  # No secrets in Dockerfile at all
  ```

- [ ] **No secrets in build context**
  ```dockerignore
  # .dockerignore must include:
  .env
  .env.*
  *.pem
  *.key
  *.p12
  secrets/
  credentials/
  ```

- [ ] **Check git history** - Ensure secrets weren't committed then removed

### .dockerignore Audit

- [ ] `.git` excluded (prevents repo exposure)
- [ ] `.env` and variants excluded
- [ ] Private keys excluded (`*.pem`, `*.key`)
- [ ] IDE config excluded (`.idea/`, `.vscode/`)
- [ ] Test files excluded (usually not needed in prod)

---

## Dockerfile Security

### Base Image

- [ ] **Version pinned** (not `latest`)
  ```dockerfile
  # BAD
  FROM python:latest

  # GOOD
  FROM python:3.12.3-slim@sha256:abc123...
  ```

- [ ] **Minimal base selected** - Use slim, alpine, or distroless when possible

- [ ] **Official or verified images** - Prefer Docker Official Images or Verified Publishers

- [ ] **Known CVE scan performed**
  ```bash
  trivy image python:3.12.3-slim
  grype python:3.12.3-slim
  ```

### User Configuration

- [ ] **Non-root user created**
  ```dockerfile
  # Debian/Ubuntu
  RUN groupadd --system --gid 1001 app && \
      useradd --system --uid 1001 --gid app app

  # Alpine
  RUN addgroup --system --gid 1001 app && \
      adduser --system --uid 1001 --ingroup app app
  ```

- [ ] **USER directive set before CMD**
  ```dockerfile
  USER app
  CMD ["./myapp"]
  ```

- [ ] **Files owned by non-root user**
  ```dockerfile
  COPY --chown=app:app . /app
  ```

### File Operations

- [ ] **COPY used instead of ADD**
  ```dockerfile
  # BAD - ADD can auto-extract and fetch URLs
  ADD https://example.com/file.tar.gz /app/
  ADD archive.tar.gz /app/

  # GOOD - explicit, no surprises
  COPY archive.tar.gz /app/
  RUN tar -xzf archive.tar.gz && rm archive.tar.gz
  ```

  ADD is only acceptable for:
  - Extracting local tar files (intentionally)
  - Never for remote URLs

- [ ] **No recursive COPY without ignore**
  ```dockerfile
  # Risky if .dockerignore incomplete
  COPY . /app

  # Safer - copy specific directories
  COPY src/ /app/src/
  COPY package.json package-lock.json /app/
  ```

### Package Installation

- [ ] **No unnecessary packages**
  ```dockerfile
  # BAD
  RUN apt-get install -y vim curl wget git

  # GOOD - only what's needed
  RUN apt-get install -y --no-install-recommends ca-certificates
  ```

- [ ] **Package lists cleaned**
  ```dockerfile
  RUN apt-get update && \
      apt-get install -y --no-install-recommends pkg && \
      rm -rf /var/lib/apt/lists/*
  ```

- [ ] **Build dependencies removed**
  ```dockerfile
  # Multi-stage handles this automatically
  # If single stage, use virtual packages (Alpine):
  RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
      pip install package && \
      apk del .build-deps
  ```

### Environment Variables

- [ ] **No sensitive defaults**
  ```dockerfile
  # BAD
  ENV DATABASE_URL=postgres://user:pass@db/prod

  # GOOD - safe defaults only
  ENV LOG_LEVEL=info
  ENV PORT=8080
  ```

- [ ] **ARG not used for secrets**
  ```dockerfile
  # BAD - visible in image history
  ARG DB_PASSWORD
  RUN echo $DB_PASSWORD > /tmp/pwd

  # Secrets should be injected at runtime only
  ```

---

## Runtime Security

### Container Configuration

- [ ] **Read-only filesystem compatible**
  ```dockerfile
  # Ensure app can run with read-only root
  # Write only to designated volumes
  VOLUME ["/app/data", "/tmp"]
  ```

- [ ] **No privileged operations required**
  - Application doesn't need `--privileged`
  - No `CAP_SYS_ADMIN` or other capabilities needed

- [ ] **Healthcheck defined**
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
      CMD curl -f http://localhost:8080/health || exit 1
  ```

### Network Security

- [ ] **Only required ports exposed**
  ```dockerfile
  # Document only the ports actually used
  EXPOSE 8080
  # Don't expose debug ports, databases, etc.
  ```

- [ ] **Internal services not exposed**
  - Debug endpoints not exposed
  - Metrics endpoints properly secured

---

## Supply Chain Security

### Dependency Management

- [ ] **Lock files used and committed**
  | Language | Lock File |
  |----------|-----------|
  | Python | `uv.lock`, `poetry.lock`, `requirements.txt` (pinned) |
  | Node.js | `package-lock.json`, `pnpm-lock.yaml` |
  | Go | `go.sum` |
  | Rust | `Cargo.lock` |
  | Java | Gradle lock files |

- [ ] **Dependencies pinned to exact versions**
  ```dockerfile
  # BAD
  RUN pip install requests

  # GOOD
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  # requirements.txt: requests==2.31.0
  ```

- [ ] **Base image digest pinned**
  ```dockerfile
  FROM python:3.12.3-slim@sha256:abc123...
  ```

### Build Verification

- [ ] **Reproducible builds** - Same input produces same image
- [ ] **Build metadata included**
  ```dockerfile
  LABEL org.opencontainers.image.source="https://github.com/org/repo"
  LABEL org.opencontainers.image.revision="${GIT_SHA}"
  LABEL org.opencontainers.image.created="${BUILD_DATE}"
  ```

---

## Scanning & Verification

### Pre-Push Checks

```bash
# Scan for vulnerabilities
trivy image myapp:latest

# Check for secrets
trufflehog docker --image myapp:latest

# Lint Dockerfile
hadolint Dockerfile

# Check image size
docker images myapp:latest
```

### Recommended Tools

| Tool | Purpose | Command |
|------|---------|---------|
| Trivy | Vulnerability scanning | `trivy image IMAGE` |
| Grype | Vulnerability scanning | `grype IMAGE` |
| Hadolint | Dockerfile linting | `hadolint Dockerfile` |
| Dockle | Container linting | `dockle IMAGE` |
| Dive | Layer analysis | `dive IMAGE` |
| Trufflehog | Secret detection | `trufflehog docker --image IMAGE` |

---

## Quick Security Audit

Run this checklist for any existing Dockerfile:

```
[ ] Base image pinned with digest?
[ ] Non-root USER set?
[ ] No ENV/ARG with secrets?
[ ] .dockerignore exists and comprehensive?
[ ] Multi-stage build (no build tools in runtime)?
[ ] COPY instead of ADD?
[ ] No unnecessary packages?
[ ] HEALTHCHECK defined?
[ ] Lock files used for dependencies?
```

Score: ___ / 9

- 9/9: Production ready
- 7-8: Minor improvements needed
- 5-6: Significant security gaps
- <5: Major refactoring required
