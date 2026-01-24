---
name: containerize-service
description: |
  Production-grade container image design for any service.
  This skill should be used when users need to create Dockerfiles, review
  container security, optimize image size, or implement build best practices.
  NOT for deployment, CI/CD, or Kubernetes manifests.
---

# Containerize Service

Build production-ready container images with security-first practices.

## What This Skill Does

- Creates production-ready Dockerfiles with multi-stage builds
- Reviews existing Dockerfiles for security and optimization issues
- Generates appropriate .dockerignore files
- Recommends optimal base images for specific languages/frameworks
- Ensures deterministic, reproducible builds

## What This Skill Does NOT Do

- Publish images to registries (tagging, push strategies)
- Configure CI/CD pipelines
- Create Kubernetes manifests or Helm charts
- Set up Docker Compose for orchestration
- Configure container runtime flags (`docker run` options)
- Handle deployment strategies

---

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Language, framework, existing Dockerfile, .dockerignore, dependency files |
| **Conversation** | User's specific requirements, constraints, preferences |
| **Skill References** | Domain patterns from `references/` (base images, multi-stage, security) |

### Detection Checklist

1. **Project language/framework** - Check for:
   - `package.json` → Node.js
   - `requirements.txt`, `pyproject.toml`, `uv.lock` → Python
   - `go.mod` → Go
   - `Cargo.toml` → Rust
   - `pom.xml`, `build.gradle` → Java
   - `*.csproj` → .NET

2. **Existing containerization** - Check for:
   - `Dockerfile` → Review mode (improve existing)
   - `.dockerignore` → Audit or create
   - `docker-compose.yml` → Note but out of scope

3. **Dependencies and build artifacts** - Identify:
   - Lock files (for deterministic builds)
   - Build output directories
   - Static assets

---

## Required Clarifications

Only ask about USER-SPECIFIC requirements (domain expertise is embedded in this skill):

| Clarification | Why | Default |
|---------------|-----|---------|
| Target environment constraints? | Alpine musl vs glibc compatibility | None assumed |
| Specific security requirements? | Compliance, scanning tools | Standard hardening |
| Size vs build-time tradeoff? | Optimization priority | Balanced |
| Health check endpoint? | For HEALTHCHECK directive | Infer from framework |

---

## Build Strategy Selection

### Base Image Decision Tree

```
Is your binary statically linked?
├── Yes → Use `scratch` (smallest possible)
└── No → Does it need a shell for debugging?
    ├── No → Use `distroless` (minimal, no shell)
    └── Yes → Is musl libc compatible?
        ├── Yes → Use `alpine` variant (~5MB base)
        └── No → Use `slim` variant (~80MB base)
```

### Language-Specific Recommendations

| Language | Recommended Base | Alternative | Notes |
|----------|------------------|-------------|-------|
| Go | `scratch` | `distroless/static` | CGO_ENABLED=0 required |
| Rust | `scratch` | `distroless/cc` | Static linking with musl |
| Python | `python:3.x-slim` | `distroless/python3` | Slim for debugging |
| Node.js | `node:lts-alpine` | `distroless/nodejs` | Alpine if shell needed |
| Java | `eclipse-temurin:*-jre-alpine` | `distroless/java` | JRE only, not JDK |
| .NET | `mcr.microsoft.com/dotnet/runtime-deps` | Alpine variant | Self-contained apps |

See `references/base-images.md` for detailed guidance.

---

## Dockerfile Structure

### Multi-Stage Template (Language-Agnostic)

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Build
# ============================================
FROM <builder-image>:<version>@sha256:<digest> AS builder

WORKDIR /build

# Copy dependency files first (cache optimization)
COPY <lockfile> <manifest> ./

# Install dependencies
RUN <install-deps-command>

# Copy source code
COPY . .

# Build application
RUN <build-command>

# ============================================
# Stage 2: Runtime
# ============================================
FROM <runtime-image>:<version>@sha256:<digest> AS runtime

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

WORKDIR /app

# Copy built artifacts from builder
COPY --from=builder --chown=appuser:appgroup /build/<output> .

# Switch to non-root user
USER appuser

# Expose port (documentation only)
EXPOSE <port>

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD <health-check-command>

# Runtime command
CMD ["<entrypoint>"]
```

### Label Conventions (OCI Standard)

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL org.opencontainers.image.description="Service description"
LABEL org.opencontainers.image.version="1.0.0"
```

See `references/multi-stage-patterns.md` for language-specific patterns.

---

## Deterministic Build Requirements

### Base Image Pinning

```dockerfile
# BAD - unpinned, not reproducible
FROM python:3.12

# GOOD - version pinned
FROM python:3.12.3-slim

# BEST - version + digest pinned (fully reproducible)
FROM python:3.12.3-slim@sha256:abc123...
```

**How to get digest:**
```bash
docker pull python:3.12.3-slim
docker inspect --format='{{index .RepoDigests 0}}' python:3.12.3-slim
```

### Dependency Lock Files

| Language | Lock File | Command to Generate |
|----------|-----------|---------------------|
| Python (uv) | `uv.lock` | `uv lock` |
| Python (pip) | `requirements.txt` (pinned) | `pip freeze > requirements.txt` |
| Node.js | `package-lock.json` | `npm install` |
| Go | `go.sum` | `go mod tidy` |
| Rust | `Cargo.lock` | `cargo build` |

**Always copy lock files before installing:**
```dockerfile
COPY package.json package-lock.json ./
RUN npm ci  # Uses lock file exactly
```

---

## Runtime Configuration Patterns

### Principle: Images are Immutable, Config is External

**Never bake into image:**
- Database connection strings
- API keys and secrets
- Environment-specific URLs
- Feature flags

**Use ENV for defaults only:**
```dockerfile
# Safe - overridable defaults
ENV LOG_LEVEL=info
ENV PORT=8080

# UNSAFE - never do this
ENV DATABASE_URL=postgres://prod:secret@db/app
```

### Configuration Injection Methods

| Method | Use Case | Example |
|--------|----------|---------|
| Environment variables | Simple key-value | `-e LOG_LEVEL=debug` |
| Environment file | Multiple variables | `--env-file .env.local` |
| Config file mount | Complex configuration | `-v ./config.yaml:/app/config.yaml:ro` |
| Secrets mount | Sensitive data | Docker secrets, K8s secrets |

### 12-Factor Compliance

1. **Codebase** - One repo, many deploys
2. **Dependencies** - Explicitly declared (lock files)
3. **Config** - Stored in environment, not code
4. **Backing services** - Attached resources via config
5. **Build, release, run** - Strict separation

See `references/runtime-config.md` for detailed patterns.

---

## .dockerignore Template

```dockerignore
# Version control
.git
.gitignore

# Dependencies (reinstalled in container)
node_modules/
__pycache__/
*.pyc
.venv/
venv/
target/
vendor/

# Build outputs
dist/
build/
*.egg-info/

# IDE and editor
.idea/
.vscode/
*.swp
*.swo

# Environment and secrets
.env
.env.*
*.pem
*.key
secrets/

# Documentation (not needed in image)
*.md
docs/

# Tests (usually not needed in prod image)
tests/
test/
*_test.go
*.test.js

# Docker files (prevent recursive issues)
Dockerfile*
docker-compose*
.dockerignore
```

---

## Output Checklist

Before delivering, verify:

### Security
- [ ] No secrets in image layers (ENV, ARG, COPY)
- [ ] Non-root user configured (USER directive)
- [ ] .dockerignore excludes sensitive files (.env, keys, secrets/)
- [ ] No unnecessary packages installed
- [ ] COPY used instead of ADD (unless extracting archives)

### Optimization
- [ ] Multi-stage build used (separate builder/runtime)
- [ ] Minimal base image selected and justified
- [ ] Dependencies copied before source (cache optimization)
- [ ] RUN commands consolidated where appropriate

### Reproducibility
- [ ] Base image version pinned (no `latest`)
- [ ] Base image digest included for production
- [ ] Lock files copied and used for dependency installation
- [ ] No floating version specifiers in package installs

### Runtime
- [ ] HEALTHCHECK defined with appropriate intervals
- [ ] PORT exposed (documentation)
- [ ] Configuration externalized (not baked)
- [ ] Appropriate CMD/ENTRYPOINT form used

See `references/security-checklist.md` for detailed security review.

---

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| `FROM ubuntu:latest` | Unpinned, bloated | Pin version, use slim/alpine |
| `COPY . .` first | Breaks cache on any change | Copy deps first, then source |
| Secrets in ENV/ARG | Visible in image layers | Runtime injection only |
| Running as root | Security vulnerability | Add USER directive |
| Single-stage build | Includes build tools in runtime | Use multi-stage |
| `apt-get install -y pkg` | Installs recommends | Add `--no-install-recommends` |
| No .dockerignore | Copies .git, secrets, etc. | Create comprehensive ignore |

See `references/anti-patterns.md` for complete list.

---

## Reference Files

| File | Purpose | When to Read |
|------|---------|--------------|
| `references/base-images.md` | Detailed base image selection | Choosing base image |
| `references/multi-stage-patterns.md` | Language-specific patterns | Writing Dockerfile |
| `references/security-checklist.md` | Security hardening | Final review |
| `references/runtime-config.md` | Configuration patterns | Handling config/secrets |
| `references/anti-patterns.md` | Common mistakes | Review/debugging |
