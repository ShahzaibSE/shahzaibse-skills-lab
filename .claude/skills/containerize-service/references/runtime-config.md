# Runtime Configuration Patterns

How to properly externalize configuration for containerized applications.

---

## Core Principle

**Images are immutable artifacts. Configuration is injected at runtime.**

The same image should run in dev, staging, and production with different configurations.

---

## 12-Factor App Configuration

### The Rules

1. **Config varies between deploys; code does not**
2. **Store config in environment variables**
3. **Never commit secrets to repository**
4. **Never bake environment-specific config into images**

### What IS Configuration?

- Database connection strings
- API endpoints and URLs
- Feature flags
- Logging levels
- External service credentials
- Port numbers
- Resource limits

### What IS NOT Configuration?

- Application code
- Static assets
- Internal constants that don't vary
- Compile-time configuration

---

## ARG vs ENV

| Directive | Available | Persisted | Use For |
|-----------|-----------|-----------|---------|
| `ARG` | Build time only | No (not in image) | Build-time variables (versions, flags) |
| `ENV` | Build + runtime | Yes (in image) | Runtime defaults (can override) |

### ARG Examples (Build-Time)

```dockerfile
# Version selection
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Build flags
ARG BUILD_ENV=production
RUN if [ "$BUILD_ENV" = "development" ]; then pip install pytest; fi

# Git commit for labeling
ARG GIT_SHA
LABEL org.opencontainers.image.revision=${GIT_SHA}
```

### ENV Examples (Runtime Defaults)

```dockerfile
# Safe defaults - can be overridden at runtime
ENV LOG_LEVEL=info
ENV PORT=8080
ENV WORKERS=4

# Application-specific defaults
ENV APP_ENV=production
ENV ENABLE_METRICS=true
```

---

## Configuration Injection Methods

### 1. Environment Variables (Simple)

```bash
# Single variable
docker run -e LOG_LEVEL=debug myapp

# Multiple variables
docker run -e LOG_LEVEL=debug -e PORT=9000 myapp
```

**Use for:**
- Simple key-value configuration
- Single values that vary per environment
- Feature flags

### 2. Environment File (Multiple Variables)

```bash
# .env.local
LOG_LEVEL=debug
DATABASE_HOST=localhost
CACHE_TTL=3600

# Run with env file
docker run --env-file .env.local myapp
```

**Use for:**
- Multiple related configuration values
- Environment-specific config bundles
- Non-sensitive configuration

### 3. Config File Mount (Complex)

```bash
# Mount read-only config file
docker run -v ./config.yaml:/app/config.yaml:ro myapp
```

**Use for:**
- Complex, structured configuration
- YAML/JSON/TOML config files
- Configuration with nested structures

### 4. Secrets (Sensitive Data)

```bash
# Docker secrets (Swarm)
docker secret create db_password ./password.txt
docker service create --secret db_password myapp

# Kubernetes secrets (mounted as files)
# Secret appears at /run/secrets/db_password
```

**Use for:**
- Passwords, API keys, tokens
- Certificates and private keys
- Any sensitive data

---

## Pattern: Configuration File

### Dockerfile

```dockerfile
# Don't copy config files into image
# Just ensure the app reads from a known path

WORKDIR /app
COPY --chown=app:app . .

# Document the expected config location
# Config will be mounted at runtime
VOLUME ["/app/config"]

CMD ["./app", "--config", "/app/config/settings.yaml"]
```

### Runtime

```bash
# Mount config directory
docker run \
  -v ./config/production.yaml:/app/config/settings.yaml:ro \
  myapp
```

---

## Pattern: Environment Variable Precedence

Application should read configuration with this precedence:

1. **Command-line arguments** (highest)
2. **Environment variables**
3. **Config file**
4. **Defaults** (lowest)

### Python Example

```python
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
PORT = int(os.getenv("PORT", "8080"))
DATABASE_URL = os.environ["DATABASE_URL"]  # Required - no default
```

### Node.js Example

```javascript
const config = {
  logLevel: process.env.LOG_LEVEL || 'info',
  port: parseInt(process.env.PORT || '8080'),
  databaseUrl: process.env.DATABASE_URL, // Required
};
```

---

## Anti-Patterns to Avoid

### 1. Baking Secrets into Image

```dockerfile
# NEVER do this
COPY .env /app/.env
ENV DATABASE_URL=postgres://user:pass@prod-db/app
```

**Why bad:** Secrets visible in image layers, persisted forever.

### 2. ARG to ENV for Secrets

```dockerfile
# NEVER do this
ARG DB_PASSWORD
ENV DB_PASSWORD=$DB_PASSWORD
```

**Why bad:** Still visible in image history via `docker history`.

### 3. Fetching Secrets at Build Time

```dockerfile
# NEVER do this
RUN curl -o /app/secrets.json https://vault.example.com/secrets
```

**Why bad:** Bakes secrets into image layer.

### 4. Different Images per Environment

```dockerfile
# NEVER do this
# Dockerfile.dev, Dockerfile.staging, Dockerfile.prod
```

**Why bad:** Violates 12-factor, untested production images.

---

## Secrets Best Practices

### What NOT to Put in Image

- Passwords
- API keys and tokens
- Database connection strings with credentials
- Private keys and certificates
- OAuth client secrets

### Safe Patterns

```bash
# Environment variable at runtime
docker run -e DATABASE_URL="postgres://..." myapp

# Mount secrets file
docker run -v ./secrets:/run/secrets:ro myapp

# Docker secrets (Swarm)
docker service create \
  --secret source=db_pass,target=/run/secrets/db_password \
  myapp

# Kubernetes secrets
kubectl create secret generic db-creds \
  --from-literal=password=mysecret
```

### Application Code

```python
# Read secret from file (mounted at runtime)
def get_secret(name):
    secret_path = f"/run/secrets/{name}"
    if os.path.exists(secret_path):
        with open(secret_path) as f:
            return f.read().strip()
    return os.getenv(name.upper())

db_password = get_secret("db_password")
```

---

## Quick Reference

| Configuration Type | Method | Example |
|--------------------|--------|---------|
| Simple values | ENV override | `-e LOG_LEVEL=debug` |
| Multiple values | Env file | `--env-file .env.local` |
| Complex config | Mount file | `-v config.yaml:/app/config.yaml:ro` |
| Secrets | Secrets mount | `--secret db_password` |
| Required values | No default in code | `os.environ["KEY"]` |
| Optional values | Default in code | `os.getenv("KEY", "default")` |
