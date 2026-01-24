# Multi-Stage Build Patterns

Language-specific patterns for optimal multi-stage Docker builds.

## Why Multi-Stage?

| Single Stage | Multi-Stage |
|--------------|-------------|
| Build tools in final image | Build tools discarded |
| Larger image size | Minimal runtime only |
| More CVE surface | Reduced attack surface |
| Slower deploys | Faster deploys |

---

## Python (uv - Recommended)

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# Build stage
# ============================================
FROM python:3.12.3-slim@sha256:... AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source and install project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# Runtime stage
# ============================================
FROM python:3.12.3-slim@sha256:... AS runtime

# Create non-root user
RUN groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid app app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application code
COPY --from=builder --chown=app:app /app/src ./src

# Add venv to path
ENV PATH="/app/.venv/bin:$PATH"

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "-m", "src.main"]
```

---

## Python (pip)

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12.3-slim@sha256:... AS builder

WORKDIR /app

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# ============================================
FROM python:3.12.3-slim@sha256:... AS runtime

RUN groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid app app

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application
COPY --chown=app:app . .

USER app
EXPOSE 8000

CMD ["python", "main.py"]
```

---

## Python (Poetry)

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12.3-slim@sha256:... AS builder

ENV POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --only=main --no-root

COPY . .
RUN poetry install --only=main

# ============================================
FROM python:3.12.3-slim@sha256:... AS runtime

RUN groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid app app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src ./src

ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000

CMD ["python", "-m", "src.main"]
```

---

## Node.js (npm)

```dockerfile
# syntax=docker/dockerfile:1

FROM node:20.11-alpine@sha256:... AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install all dependencies (including dev for build)
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Prune dev dependencies
RUN npm prune --production

# ============================================
FROM node:20.11-alpine@sha256:... AS runtime

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nodejs

WORKDIR /app

# Copy production dependencies
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules

# Copy built application
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./

USER nodejs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

---

## Node.js (pnpm)

```dockerfile
# syntax=docker/dockerfile:1

FROM node:20.11-alpine@sha256:... AS builder

RUN corepack enable pnpm

WORKDIR /app

COPY pnpm-lock.yaml package.json ./
RUN pnpm fetch

COPY . .
RUN pnpm install --offline --frozen-lockfile
RUN pnpm build
RUN pnpm prune --prod

# ============================================
FROM node:20.11-alpine@sha256:... AS runtime

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nodejs

WORKDIR /app

COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./

USER nodejs
EXPOSE 3000

CMD ["node", "dist/index.js"]
```

---

## Go

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.22-alpine@sha256:... AS builder

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /app ./cmd/server

# ============================================
FROM scratch AS runtime

# Copy CA certificates for HTTPS
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy binary
COPY --from=builder /app /app

EXPOSE 8080

ENTRYPOINT ["/app"]
```

### Go with CGO (needs glibc)

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.22-alpine@sha256:... AS builder

RUN apk add --no-cache gcc musl-dev

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -ldflags="-s -w" -o /app ./cmd/server

# ============================================
FROM gcr.io/distroless/base@sha256:... AS runtime

COPY --from=builder /app /app

EXPOSE 8080

ENTRYPOINT ["/app"]
```

---

## Rust

```dockerfile
# syntax=docker/dockerfile:1

FROM rust:1.76-alpine@sha256:... AS builder

RUN apk add --no-cache musl-dev

WORKDIR /build

# Cache dependencies
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release --target x86_64-unknown-linux-musl
RUN rm -rf src

# Build actual application
COPY . .
RUN touch src/main.rs  # Force rebuild
RUN cargo build --release --target x86_64-unknown-linux-musl

# ============================================
FROM scratch AS runtime

COPY --from=builder /build/target/x86_64-unknown-linux-musl/release/app /app

EXPOSE 8080

ENTRYPOINT ["/app"]
```

---

## Java (Maven)

```dockerfile
# syntax=docker/dockerfile:1

FROM maven:3.9-eclipse-temurin-21-alpine@sha256:... AS builder

WORKDIR /build

# Cache dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Build
COPY src ./src
RUN mvn package -DskipTests -B

# ============================================
FROM eclipse-temurin:21-jre-alpine@sha256:... AS runtime

RUN addgroup --system --gid 1001 java && \
    adduser --system --uid 1001 --ingroup java java

WORKDIR /app

COPY --from=builder --chown=java:java /build/target/*.jar app.jar

USER java
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## Java (Gradle)

```dockerfile
# syntax=docker/dockerfile:1

FROM gradle:8.5-jdk21-alpine@sha256:... AS builder

WORKDIR /build

# Cache dependencies
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle ./gradle
RUN gradle dependencies --no-daemon

# Build
COPY src ./src
RUN gradle build -x test --no-daemon

# ============================================
FROM eclipse-temurin:21-jre-alpine@sha256:... AS runtime

RUN addgroup --system --gid 1001 java && \
    adduser --system --uid 1001 --ingroup java java

WORKDIR /app

COPY --from=builder --chown=java:java /build/build/libs/*.jar app.jar

USER java
EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## .NET

```dockerfile
# syntax=docker/dockerfile:1

FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine@sha256:... AS builder

WORKDIR /build

# Cache dependencies
COPY *.csproj ./
RUN dotnet restore

# Build
COPY . .
RUN dotnet publish -c Release -o /app --no-restore

# ============================================
FROM mcr.microsoft.com/dotnet/runtime-deps:8.0-alpine@sha256:... AS runtime

RUN addgroup --system --gid 1001 dotnet && \
    adduser --system --uid 1001 -G dotnet dotnet

WORKDIR /app

COPY --from=builder --chown=dotnet:dotnet /app .

USER dotnet
EXPOSE 8080

ENTRYPOINT ["./MyApp"]
```

---

## Cache Optimization Tips

### BuildKit Cache Mounts

```dockerfile
# Python pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Go modules cache
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Rust cargo cache
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    cargo build --release
```

### Layer Ordering

```dockerfile
# GOOD: Dependencies change less often than source
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# BAD: Any source change invalidates npm install cache
COPY . .
RUN npm ci
```
